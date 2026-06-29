import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Local Modules
import models
import schemas
from database import engine, get_db
from services.gemini_service import analyze_audio
from services.pdf_service import generate_pdf_report

# Initialize Database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="OS Precision Audit API")

# Configure CORS to accept requests from Frontend port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure local directories exist
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")

for folder in [UPLOADS_DIR, REPORTS_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Mount the reports directory statically to serve PDF downloads
app.mount("/api/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

@app.post("/api/audit")
async def audit_call(
    agent_name: str = Form(...),
    call_id: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Setup metadata
    if not call_id:
        call_id = f"CALL-{int(datetime.now().timestamp())}"
    
    # Check for duplicate Call ID
    existing = db.query(models.CallAudit).filter(models.CallAudit.call_id == call_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Call ID already exists in the system database.")

    # 2. Save uploaded audio file locally
    file_extension = os.path.splitext(audio.filename)[1] or ".mp3"
    temp_filename = f"upload_{call_id}{file_extension}"
    temp_filepath = os.path.join(UPLOADS_DIR, temp_filename)

    try:
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded audio: {str(e)}")

    # 3. Process with Gemini and perform cleanups
    try:
        mime_type = audio.content_type or "audio/mpeg"
        result = analyze_audio(temp_filepath, display_name=f"Audio_{call_id}")
        
        # Calculate sub-scores based on Gemini infraction counts
        cc_score = max(0, min(100, 100 - (result.get("NC", 0) * 10)))
        bc_score = max(0, min(100, 100 - (result.get("BC", 0) * 10)))
        
        # Immediate fail for critical error (EC)
        ec_score = 0 if result.get("EC", 0) > 0 else 100
        
        # Next steps score based on greeting/closing NC counts
        nc_score = max(0, min(100, 100 - (result.get("NC", 0) * 10)))
        
        # Calculate total score average
        avg_score = round((cc_score + bc_score + ec_score + nc_score) / 4)
        
        # Override status if EC is committed
        final_status = "Fail" if (ec_score == 0 or avg_score < 70) else result.get("status", "Pass")

        # Compile list of errors from failed checklist items
        failed_items = [
            f"[{item.get('category')}] {item.get('description')} ({item.get('timestamp')})"
            for item in result.get("detailed_scoring", [])
            if item.get("pass_fail", "").lower() == "fail"
        ]
        errors_str = ", ".join(failed_items) if failed_items else "None"

        # 4. Generate PDF Report locally
        pdf_filename = f"report_{call_id}.pdf"
        evaluation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        pdf_payload = {
            "agent_name": agent_name,
            "call_id": call_id,
            "evaluation_date": evaluation_date,
            "status": final_status,
            "total_score": f"{avg_score}%",
            "cc_score": cc_score,
            "bc_score": bc_score,
            "ec_score": ec_score,
            "nc_score": nc_score,
            "nc_count": result.get("NC", 0),
            "bc_count": result.get("BC", 0),
            "ec_count": result.get("EC", 0),
            "errors": errors_str,
            "detailed_scoring": result.get("detailed_scoring", []),
            "ai_feedback": result.get("coaching_summary", "")
        }

        generate_pdf_report(pdf_payload, pdf_filename)
        pdf_download_url = f"http://localhost:5000/api/reports/{pdf_filename}"

        # 5. Write record to SQLite DB
        db_audit = models.CallAudit(
            agent_name=agent_name,
            call_id=call_id,
            evaluation_date=evaluation_date,
            status=final_status,
            total_score=f"{avg_score}%",
            pdf_report_path=pdf_download_url,
            cc_score=cc_score,
            bc_score=bc_score,
            ec_score=ec_score,
            nc_score=nc_score,
            errors=errors_str,
            ai_feedback=result.get("coaching_summary", "")
        )
        db.add(db_audit)
        db.commit()
        db.refresh(db_audit)

        # Map return object format expected by Frontend
        return {
            "success": True,
            "data": {
                "id": db_audit.id,
                "Call_ID": db_audit.call_id,
                "Agent_Name": db_audit.agent_name,
                "Call_Timestamp": db_audit.evaluation_date,
                "Pass_Fail": db_audit.status,
                "Total_Score": db_audit.total_score,
                "CC": db_audit.cc_score,
                "BC": db_audit.bc_score,
                "EC": db_audit.ec_score,
                "NC": db_audit.nc_score,
                "Errors": db_audit.errors,
                "AI_Feedback": db_audit.ai_feedback,
                "doc_url": db_audit.pdf_report_path
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Strict Lifecycle audio file cleanup from local storage
        if os.path.exists(temp_filepath):
            try:
                print(f"Executing automatic local file cleanup: removing {temp_filepath}...")
                os.remove(temp_filepath)
                print("Local file deleted successfully.")
            except Exception as cleanup_err:
                print(f"Failed to delete local temp audio: {cleanup_err}")

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    audits = db.query(models.CallAudit).order_by(models.CallAudit.id.desc()).all()
    
    # Map SQLAlchemy models to exact JSON payload properties expected by React
    history_list = []
    for a in audits:
        history_list.append({
            "id": a.id,
            "Call_ID": a.call_id,
            "Agent_Name": a.agent_name,
            "Call_Timestamp": a.evaluation_date,
            "Pass_Fail": a.status,
            "Total_Score": a.total_score,
            "CC": a.cc_score,
            "BC": a.bc_score,
            "EC": a.ec_score,
            "NC": a.nc_score,
            "Errors": a.errors,
            "AI_Feedback": a.ai_feedback,
            "doc_url": a.pdf_report_path
        })
    return {"success": True, "data": history_list}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    audits = db.query(models.CallAudit).all()
    total_audits = len(audits)
    
    if total_audits == 0:
        return {
            "success": True,
            "data": {
                "totalAudits": 0,
                "passRate": "0%",
                "avgScore": 0,
                "avgCC": 0,
                "avgBC": 0,
                "avgEC": 0,
                "avgNC": 0,
                "trends": [],
                "agentRankings": []
            }
        }

    passes = sum(1 for a in audits if a.status == "Pass")
    pass_rate = f"{round((passes / total_audits) * 100)}%"

    # Compute averages
    sum_score = sum(int(a.total_score.replace("%", "")) for a in audits)
    avg_score = round(sum_score / total_audits)

    avg_cc = round(sum(a.cc_score for a in audits) / total_audits)
    avg_bc = round(sum(a.bc_score for a in audits) / total_audits)
    avg_ec = round(sum(a.ec_score for a in audits) / total_audits)
    avg_nc = round(sum(a.nc_score for a in audits) / total_audits)

    # Compile trend list (last 10 audits chronologically)
    sorted_audits = sorted(audits, key=lambda x: x.id)
    trends = []
    for a in sorted_audits[-10:]:
        try:
            date_obj = datetime.strptime(a.evaluation_date, "%Y-%m-%d %H:%M:%S")
            formatted_date = date_obj.strftime("%m/%d %H:%M")
        except Exception:
            formatted_date = a.evaluation_date[:11] if a.evaluation_date else "Unknown"
        trends.append({
            "name": formatted_date,
            "score": int(a.total_score.replace("%", "")),
            "agent": a.agent_name
        })

    # Group scores by agent for ranking leaderboard
    agent_stats = {}
    for a in audits:
        score_val = int(a.total_score.replace("%", ""))
        if a.agent_name not in agent_stats:
            agent_stats[a.agent_name] = {"sum": 0, "count": 0}
        agent_stats[a.agent_name]["sum"] += score_val
        agent_stats[a.agent_name]["count"] += 1

    agent_rankings = []
    for name, stat in agent_stats.items():
        agent_rankings.append({
            "name": name,
            "avgScore": round(stat["sum"] / stat["count"]),
            "count": stat["count"]
        })
    agent_rankings = sorted(agent_rankings, key=lambda x: x["avgScore"], reverse=True)[:5]

    return {
        "success": True,
        "data": {
            "totalAudits": total_audits,
            "passRate": pass_rate,
            "avgScore": avg_score,
            "avgCC": avg_cc,
            "avgBC": avg_bc,
            "avgEC": avg_ec,
            "avgNC": avg_nc,
            "trends": trends,
            "agentRankings": agent_rankings
        }
    }
