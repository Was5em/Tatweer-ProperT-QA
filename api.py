import os
import json
import tempfile
import traceback
import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
import pandas as pd

from config import QAConfig
from database import SessionLocal, User, AnalysisQueue, ActivityLog, UsageLog, PromptConfig, AuthManager, DataManager
from core import background_analysis, SECTION_MAX, OFFICIAL_SCORECARD_PROMPT, PDFManager

app = FastAPI(title="Tatweer ProperT QA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_db():
    DataManager.init_db(default_prompt=OFFICIAL_SCORECARD_PROMPT, default_section_max=SECTION_MAX)

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str

class UserEditRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: str

class ApproveRequest(BaseModel):
    task_id: int
    call_id: str
    agent_name: str

class PromptConfigEdit(BaseModel):
    prompt_text: str
    section_max: dict

class EditHistoryRequest(BaseModel):
    agent_name: str
    score: int
    status: str

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.split(" ")[1]
    username, role = AuthManager.verify_session(token)
    if not username or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )
    return {"username": username, "role": role}

def get_admin_user(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user

def get_supervisor_user(current_user=Depends(get_current_user)):
    if current_user["role"] not in ("admin", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor or Admin access required",
        )
    return current_user

@app.post("/api/auth/login")
def login(req: LoginRequest):
    is_valid, role = AuthManager.authenticate(req.username, req.password)
    if is_valid:
        token = AuthManager.sign_session(req.username, role)
        DataManager.log_activity(req.username, "Logged In")
        return {"token": token, "username": req.username, "role": role.lower()}
    raise HTTPException(status_code=400, detail="Invalid username or password")

@app.get("/api/auth/me")
def get_me(current_user=Depends(get_current_user)):
    return current_user

@app.post("/api/analysis/upload")
def upload_files(
    files: List[UploadFile] = File(...),
    current_user=Depends(get_current_user)
):
    temp_dir = "./temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    queued_count = 0
    for file in files:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        
        item_id = DataManager.add_to_queue(file.filename)
        
        task_path = tmp_path
        if QAConfig.is_s3_enabled():
            try:
                s3_key = f"audios/{item_id}_{file.filename}"
                from storage import S3Manager
                S3Manager.upload_file(tmp_path, s3_key)
                with SessionLocal() as db:
                    queue_item = db.query(AnalysisQueue).filter(AnalysisQueue.id == item_id).first()
                    if queue_item:
                        queue_item.s3_key = s3_key
                        db.commit()
                task_path = s3_key
            except Exception as s3_err:
                with SessionLocal() as db:
                    queue_item = db.query(AnalysisQueue).filter(AnalysisQueue.id == item_id).first()
                    if queue_item:
                        db.delete(queue_item)
                        db.commit()
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
                raise HTTPException(
                    status_code=500,
                    detail=f"S3 Upload failed for {file.filename}: {str(s3_err)}"
                )
        
        if os.environ.get("CELERY_BROKER_URL"):
            try:
                from tasks import run_analysis_task
                run_analysis_task.delay(item_id, task_path)
            except Exception:
                import concurrent.futures
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
                executor.submit(background_analysis, item_id, task_path)
        else:
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
            executor.submit(background_analysis, item_id, task_path)
            
        if QAConfig.is_s3_enabled():
            try:
                os.remove(tmp_path)
            except OSError:
                pass
                
        queued_count += 1

    DataManager.log_activity(current_user["username"], f"Uploaded and queued {queued_count} files")
    return {"message": f"Successfully queued {queued_count} files for analysis."}

@app.get("/api/analysis/queue")
def get_queue(current_user=Depends(get_current_user)):
    with SessionLocal() as db:
        queue = db.query(AnalysisQueue).order_by(AnalysisQueue.id.desc()).limit(15).all()
        return [
            {
                "id": item.id,
                "filename": item.filename,
                "status": item.status,
                "error_msg": item.error_msg,
                "created_at": item.created_at
            }
            for item in queue
        ]

@app.get("/api/review/list")
def get_review_list(show_verified: bool = False, current_user=Depends(get_current_user)):
    with SessionLocal() as db:
        query = db.query(AnalysisQueue.id, AnalysisQueue.filename, AnalysisQueue.created_at, AnalysisQueue.call_id).filter(
            AnalysisQueue.status == "Completed"
        )
        if not show_verified:
            query = query.filter((AnalysisQueue.call_id == None) | (AnalysisQueue.call_id == ""))
        tasks = query.all()
        return [
            {
                "id": t.id,
                "filename": t.filename,
                "created_at": t.created_at,
                "call_id": t.call_id,
                "is_verified": bool(t.call_id)
            }
            for t in tasks
        ]

@app.get("/api/review/report/{task_id}")
def get_report(task_id: int, current_user=Depends(get_current_user)):
    with SessionLocal() as db:
        task = db.query(AnalysisQueue).filter(AnalysisQueue.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Report not found")
        try:
            report_data = json.loads(task.result_json) if task.result_json else {}
            return {
                "id": task.id,
                "filename": task.filename,
                "call_id": task.call_id,
                "created_at": task.created_at,
                "report": report_data
            }
        except Exception:
            raise HTTPException(status_code=500, detail="Could not parse report data")

@app.post("/api/review/approve")
def approve_report(req: ApproveRequest, current_user=Depends(get_current_user)):
    with SessionLocal() as db:
        task = db.query(AnalysisQueue).filter(AnalysisQueue.id == req.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        try:
            res = json.loads(task.result_json)
        except Exception:
            raise HTTPException(status_code=500, detail="Corrupted task data")

        res['Call_ID'] = req.call_id
        res['Agent_Name'] = req.agent_name
        
        pdf_url = None
        if QAConfig.is_s3_enabled():
            try:
                pdf_data = PDFManager.create_full_pdf(res)
                s3_key = f"reports/Audit_{req.call_id}.pdf"
                from storage import S3Manager
                pdf_url = S3Manager.upload_bytes(pdf_data, s3_key, content_type="application/pdf")
                res['pdf_url'] = pdf_url
            except Exception as pdf_err:
                print(f"S3 PDF upload failed: {pdf_err}")
                
        DataManager.save_call_to_history(res)
        DataManager.link_queue_to_call(req.task_id, req.call_id, pdf_url=pdf_url)
        DataManager.log_activity(current_user["username"], f"Approved and saved call {req.call_id}")
        return {"message": "Call approved and saved to audit history."}

@app.get("/api/review/download/{task_id}")
def download_pdf(task_id: int):
    with SessionLocal() as db:
        task = db.query(AnalysisQueue).filter(AnalysisQueue.id == task_id).first()
        if not task:
            return Response(status_code=404, content="Report not found")
        try:
            res = json.loads(task.result_json)
        except Exception:
            return Response(status_code=500, content="Corrupted report data")
        
        pdf_data = None
        if QAConfig.is_s3_enabled() and task.pdf_url:
            try:
                from storage import S3Manager
                call_id = res.get("Call_ID", "")
                s3_key = f"reports/Audit_{call_id or task_id}.pdf"
                client = S3Manager.get_client()
                cfg = QAConfig.get_s3_config()
                s3_response = client.get_object(Bucket=cfg["bucket"], Key=s3_key)
                pdf_data = s3_response['Body'].read()
            except Exception as e:
                print(f"S3 PDF download failed, falling back to dynamic generation: {e}")
                pdf_data = PDFManager.create_full_pdf(res)
        else:
            pdf_data = PDFManager.create_full_pdf(res)
            
        headers = {
            'Content-Disposition': f'attachment; filename="Audit_{task_id}.pdf"',
            'Content-Type': 'application/pdf'
        }
        return Response(content=pdf_data, headers=headers)

def get_period_start(period: str):
    import datetime
    now = datetime.datetime.now()
    if period == "Today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "Last 7 Days":
        return now - datetime.timedelta(days=7)
    elif period == "Last 30 Days":
        return now - datetime.timedelta(days=30)
    return None

@app.get("/api/dashboard/stats")
def get_dashboard_stats(period: str = "Overall Total", current_user=Depends(get_current_user)):
    df_full = DataManager.get_all_history()
    if df_full.empty:
        return {"total_audits": 0, "avg_score": 0, "sales_closed": 0, "pass_rate": 0, "transfers": 0}
    
    df = df_full.copy()
    start = get_period_start(period)
    if start:
        df['timestamp_dt'] = datetime_helper(df['timestamp'])
        df = df[df['timestamp_dt'] >= start]
        
    if df.empty:
        return {"total_audits": 0, "avg_score": 0, "sales_closed": 0, "pass_rate": 0, "transfers": 0}
        
    has_transferred = "transferred" in df.columns
    has_sale        = "sale_closed" in df.columns
    has_fcr         = "fcr" in df.columns
    has_feedback    = "customer_feedback" in df.columns

    pass_count = df[df["status"].str.contains("Pass", case=False, na=False)] if "status" in df.columns else []
    pass_rate  = (len(pass_count) / len(df)) * 100 if len(df) > 0 else 0
    
    # Map sales_closed to FCR Yes count, and transfers to Positive feedback count
    sales      = int(len(df[df["fcr"].str.upper() == "YES"])) if has_fcr else (int(len(df[df["sale_closed"].str.upper() == "YES"])) if has_sale else 0)
    transfers  = int(len(df[df["customer_feedback"].str.upper() == "POSITIVE"])) if has_feedback else (int(len(df[df["transferred"].str.upper() == "YES"])) if has_transferred else 0)
    avg_score  = float(df["score"].mean()) if "score" in df.columns and not df["score"].isna().all() else 0

    return {
        "total_audits": len(df),
        "avg_score": round(avg_score, 1),
        "sales_closed": sales,
        "pass_rate": round(pass_rate, 1),
        "transfers": transfers
    }


def datetime_helper(series):
    import pandas as pd
    return pd.to_datetime(series, errors='coerce')

@app.get("/api/dashboard/charts")
def get_dashboard_charts(period: str = "Overall Total", current_user=Depends(get_current_user)):
    df_full = DataManager.get_all_history()
    if df_full.empty:
        return {"pie": [], "bar": [], "trend": []}
    
    df = df_full.copy()
    start = get_period_start(period)
    if start:
        df['timestamp_dt'] = datetime_helper(df['timestamp'])
        df = df[df['timestamp_dt'] >= start]

    if df.empty:
        return {"pie": [], "bar": [], "trend": []}

    pie_data = []
    if "status" in df.columns:
        counts = df["status"].value_counts().to_dict()
        pie_data = [{"name": k, "value": int(v)} for k, v in counts.items()]

    bar_data = []
    if "agent_name" in df.columns and "score" in df.columns:
        agent_perf = df.groupby('agent_name')['score'].mean().reset_index().sort_values('score', ascending=False)
        bar_data = [{"agent": row["agent_name"], "score": round(float(row["score"]), 1)} for _, row in agent_perf.iterrows()]

    trend_data = []
    if 'timestamp' in df.columns:
        df['timestamp_dt'] = datetime_helper(df['timestamp'])
        df_sorted = df.dropna(subset=['timestamp_dt']).sort_values('timestamp_dt')
        if not df_sorted.empty:
            df_sorted['date_str'] = df_sorted['timestamp_dt'].dt.strftime("%Y-%m-%d")
            daily_trend = df_sorted.groupby('date_str')['score'].mean().reset_index()
            trend_data = [
                {"date": row["date_str"], "score": round(float(row["score"]), 1)}
                for _, row in daily_trend.iterrows()
            ]

    return {"pie": pie_data, "bar": bar_data, "trend": trend_data}

@app.get("/api/dashboard/compliance")
def get_dashboard_compliance(period: str = "Overall Total", current_user=Depends(get_current_user)):
    start = get_period_start(period)
    start_str = start.strftime("%Y-%m-%d %H:%M:%S") if start else None
    
    with SessionLocal() as db:
        query = db.query(AnalysisQueue.result_json).filter(AnalysisQueue.status == "Completed")
        if start_str:
            query = query.filter(AnalysisQueue.created_at >= start_str)
        completed_tasks = query.all()
        
    checklists = []
    for row in completed_tasks:
        if row[0]:
            try:
                res_dict = json.loads(row[0])
                chk = res_dict.get("Compliance_Checklist", {})
                if chk:
                    checklists.append(chk)
            except Exception:
                pass
    
    items_to_show = {
        "Privacy_Check": "Privacy & Policy Verification",
        "BC_Violations": "Business Critical Compliance",
        "EC_Violations": "End-User Critical Compliance",
        "First_Call_Resolution_FCR": "First Call Resolution (FCR)",
        "Customer_Sentiment": "Positive Customer Sentiment"
    }

    if not checklists:
        return [{"key": k, "label": l, "rate": 0.0} for k, l in items_to_show.items()]

    import pandas as pd
    chk_df = pd.DataFrame(checklists)
    
    rates = []
    for key, label in items_to_show.items():
        if key in chk_df.columns:
            values = chk_df[key].astype(str).str.strip().str.upper().map(
                lambda x: 1 if x in ("YES", "TRUE", "PASS", "NONE", "POSITIVE", "Y") else 0
            )
            rate = float(values.mean() * 100)
        else:
            rate = 0.0
        rates.append({"key": key, "label": label, "rate": round(rate, 1)})
    return rates

@app.get("/api/dashboard/leaderboard")
def get_dashboard_leaderboard(period: str = "Overall Total", current_user=Depends(get_current_user)):
    df_full = DataManager.get_all_history()
    if df_full.empty:
        return []
    
    df = df_full.copy()
    start = get_period_start(period)
    if start:
        df['timestamp_dt'] = datetime_helper(df['timestamp'])
        df = df[df['timestamp_dt'] >= start]

    if df.empty:
        return []

    has_sale = "sale_closed" in df.columns
    agg_dict = {'Avg_Score': ('score', 'mean'), 'Total_Calls': ('score', 'count')}
    if has_sale:
        agg_dict['Sales_Closed'] = ('sale_closed', lambda x: int((x.str.upper() == 'YES').sum()))

    leaderboard = df.groupby('agent_name').agg(**agg_dict).reset_index().sort_values('Avg_Score', ascending=False).reset_index(drop=True)
    leaderboard['Avg_Score'] = leaderboard['Avg_Score'].round(1)

    return [
        {
            "rank": idx + 1,
            "agent_name": row["agent_name"],
            "avg_score": float(row["Avg_Score"]),
            "total_calls": int(row["Total_Calls"]),
            "sales_closed": int(row.get("Sales_Closed", 0)) if has_sale else 0
        }
        for idx, row in leaderboard.iterrows()
    ]

@app.get("/api/history/list")
def get_history_list(current_user=Depends(get_supervisor_user)):
    df = DataManager.get_all_history()
    if df.empty:
        return []
    return df.to_dict(orient="records")

@app.put("/api/history/{call_id}")
def update_history(call_id: str, req: EditHistoryRequest, current_user=Depends(get_supervisor_user)):
    DataManager.update_call_history(call_id, {
        "agent_name": req.agent_name,
        "score": req.score,
        "status": req.status
    })
    DataManager.log_activity(current_user["username"], f"Updated call history for {call_id}")
    return {"message": "Call history record updated successfully."}

@app.delete("/api/history/{call_id}")
def delete_history(call_id: str, current_user=Depends(get_admin_user)):
    DataManager.delete_call_history(call_id)
    DataManager.log_activity(current_user["username"], f"Deleted call history {call_id}")
    return {"message": "Call history record deleted."}

@app.post("/api/settings/password")
def change_password(req: PasswordRequest, current_user=Depends(get_current_user)):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == current_user["username"]).first()
        if user and AuthManager.verify_password(req.current_password, user.password_hash):
            user.password_hash = AuthManager.hash_password(req.new_password)
            db.commit()
            DataManager.log_activity(current_user["username"], "Changed Password")
            return {"message": "Password changed successfully."}
        raise HTTPException(status_code=400, detail="Incorrect current password")

@app.get("/api/settings/users")
def get_users(current_user=Depends(get_admin_user)):
    with SessionLocal() as db:
        all_users = db.query(User).all()
        return [{"id": u.id, "username": u.username, "role": u.role} for u in all_users]

@app.post("/api/settings/users")
def create_user(req: UserCreateRequest, current_user=Depends(get_admin_user)):
    with SessionLocal() as db:
        exists = db.query(User).filter(User.username == req.username).first()
        if exists:
            raise HTTPException(status_code=400, detail="Username already exists")
        db.add(User(
            username=req.username,
            password_hash=AuthManager.hash_password(req.password),
            role=req.role
        ))
        db.commit()
        DataManager.log_activity(current_user["username"], f"Created user {req.username} ({req.role})")
        return {"message": f"User {req.username} created successfully."}

@app.put("/api/settings/users/{username}")
def edit_user(username: str, req: UserEditRequest, current_user=Depends(get_admin_user)):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if req.username and req.username != username:
            dup = db.query(User).filter(User.username == req.username).first()
            if dup:
                raise HTTPException(status_code=400, detail="Username already taken")
            user.username = req.username
        if req.password:
            user.password_hash = AuthManager.hash_password(req.password)
        user.role = req.role
        db.commit()
        DataManager.log_activity(current_user["username"], f"Edited user {username}")
        return {"message": "User credentials updated."}

@app.delete("/api/settings/users/{username}")
def delete_user(username: str, current_user=Depends(get_admin_user)):
    if username == current_user["username"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.delete(user)
        db.commit()
        DataManager.log_activity(current_user["username"], f"Deleted user {username}")
        return {"message": f"User {username} deleted."}

@app.get("/api/settings/prompt")
def get_prompt_config(current_user=Depends(get_supervisor_user)):
    prompt_cfg = DataManager.get_active_prompt_config()
    current_prompt = prompt_cfg.get("prompt_text", "")
    current_weights = prompt_cfg.get("section_max", SECTION_MAX)
    if isinstance(current_weights, str):
        try:
            current_weights = json.loads(current_weights)
        except Exception:
            current_weights = SECTION_MAX
    return {"prompt_text": current_prompt, "section_max": current_weights, "defaults": SECTION_MAX}

@app.post("/api/settings/prompt")
def update_prompt_config(req: PromptConfigEdit, current_user=Depends(get_supervisor_user)):
    if DataManager.save_prompt_config(req.prompt_text, req.section_max):
        DataManager.log_activity(current_user["username"], "Updated Prompt and Scorecard Weights")
        return {"message": "AI Scorecard configuration updated and saved."}
    raise HTTPException(status_code=500, detail="Failed to save configuration")

@app.post("/api/settings/prompt/reset")
def reset_prompt_config(current_user=Depends(get_supervisor_user)):
    if DataManager.save_prompt_config(OFFICIAL_SCORECARD_PROMPT, SECTION_MAX):
        DataManager.log_activity(current_user["username"], "Reset Prompt to Defaults")
        return {"message": "Configuration reset to system defaults."}
    raise HTTPException(status_code=500, detail="Failed to reset configuration")

@app.get("/api/logs")
def get_system_logs(current_user=Depends(get_admin_user)):
    return DataManager.get_activity_logs().to_dict(orient="records")

@app.get("/api/usage")
def get_usage_stats(current_user=Depends(get_admin_user)):
    try:
        from database import engine
        with engine.connect() as conn:
            import pandas as pd
            queue_df = pd.read_sql_query(
                "SELECT id, filename, status, created_at, input_tokens, output_tokens, cost FROM analysis_queue WHERE status = 'Completed' ORDER BY created_at DESC", 
                conn
            )
            return queue_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="static", html=True), name="static")
