import os
import uuid
import asyncio
from datetime import datetime
from typing import Annotated

import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader
from pydantic_settings import BaseSettings, SettingsConfigDict
from slugify import slugify # For sanitizing filenames

# Local imports
from .database import create_db_and_tables, get_db
from .models import CallAudit
from .schemas import GeminiAuditResponse, AuditRequest


# --- Configuration ---
class Settings(BaseSettings):
    gemini_api_key: str
    upload_dir: str = "uploads"
    pdf_reports_dir: str = "pdf_reports"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure upload and reports directories exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.pdf_reports_dir, exist_ok=True)

# Configure Gemini API
genai.configure(api_key=settings.gemini_api_key)
generation_config = {
    "temperature": 0.5,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
    "response_mime_type": "application/json", # Enforce strict JSON output
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config=generation_config,
    safety_settings=safety_settings
)

# Set up Jinja2 environment for PDF templating
jinja_env = Environment(loader=FileSystemLoader("."))

# --- FastAPI App Initialization ---
app = FastAPI(
    title="OS Precision Audit Backend",
    description="Backend for call quality auditing system using FastAPI, SQLite, and Gemini 1.5 Pro.",
    version="1.0.0",
)

# Create database tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- Utility Functions ---

async def save_upload_file(upload_file: UploadFile) -> str:
    """Saves the uploaded file to the specified upload directory."""
    file_extension = upload_file.filename.split(".")[-1] if "." in upload_file.filename else "tmp"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(settings.upload_dir, unique_filename)
    try:
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)
        return file_path
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save audio file: {e}"
        )

async def process_audio_with_gemini(audio_path: str) -> GeminiAuditResponse:
    """
    Sends the audio file to Google Gemini 1.5 Pro for analysis
    and parses the strict JSON output.
    """
    try:
        # Upload the file to Gemini's ephemeral storage
        # Note: Gemini's client library often handles temporary file uploads implicitly
        # and manages their lifecycle. If explicit upload/deletion is needed,
        # genai.upload_file and genai.delete_file would be used.
        # For gemini-1.5-pro, directly passing the path in parts is common.
        audio_file_part = genai.upload_file(path=audio_path, display_name=os.path.basename(audio_path))

        # Wait for file to be ready, max 120 seconds
        status_check_interval_secs = 1
        for _ in range(120):
            if audio_file_part.state.is_processing():
                await asyncio.sleep(status_check_interval_secs)
            else:
                break
        if audio_file_part.state.is_failed():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gemini file processing failed: {audio_file_part.state.name}"
            )

        # Prompt for strict JSON output based on the Pydantic schema
        prompt_parts = [
            audio_file_part,
            """
            Analyze the provided call audio transcript for quality auditing based on standard call center metrics.
            Strictly return the output in JSON format, adhering to the following structure.
            The `detailed_scoring` array should contain objects with `timestamp`, `category`, `description`, and `pass_fail` fields.
            `EC` (Extreme/Critical Errors) automatically implies an overall "Fail" status.

            JSON Schema:
            {
                "NC": <integer>, // Normal Errors count
                "BC": <integer>, // Business Process Errors count
                "EC": <integer>, // Extreme/Critical Errors count (triggers auto-fail)
                "status": "Pass" | "Fail", // Overall call audit status
                "detailed_scoring": [
                    {
                        "timestamp": "<string>", // e.g., "00:00:30"
                        "category": "<string>", // e.g., "Opening", "Problem Resolution", "Closing"
                        "description": "<string>", // Detailed description of the action
                        "pass_fail": "Pass" | "Fail"
                    }
                ],
                "coaching_summary": "<string>" // Final auditor summary for coaching
            }
            """
        ]

        response = await gemini_model.generate_content_async(prompt_parts)
        
        # Access the text directly from parts of the response
        json_output = response.candidates[0].content.parts[0].text
        
        # Parse and validate with Pydantic schema
        audit_data = GeminiAuditResponse.model_validate_json(json_output)
        
        # Delete the ephemeral file from Gemini's storage
        genai.delete_file(audio_file_part.name)

        return audit_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini API processing failed: {e}"
        )

def generate_pdf_report(
    audit_data: GeminiAuditResponse,
    agent_name: str,
    call_id: str,
    evaluation_date: datetime
) -> str:
    """
    Generates a PDF report from the Gemini audit data using Jinja2 and xhtml2pdf.
    """
    try:
        template = jinja_env.get_template("template.html")
        
        # Calculate total_score based on error counts.
        # The prompt asks for `total_score` and then `NC`, `BC`, `EC` as errors.
        # I'll define total_score as the sum of errors (lower is better).
        # If a percentage score is desired, explicit scoring logic would be needed.

        html_content = template.render(
            agent_name=agent_name,
            call_id=call_id,
            evaluation_date=evaluation_date,
            audit_data=audit_data
        )

        pdf_filename = f"audit_report_{slugify(agent_name)}_{slugify(call_id)}_{evaluation_date.strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = os.path.join(settings.pdf_reports_dir, pdf_filename)

        from xhtml2pdf import pisa
        with open(pdf_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
        
        if pisa_status.err:
            raise Exception(f"xhtml2pdf error compiling report PDF: code {pisa_status.err}")
            
        return pdf_path
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {e}"
        )

def cleanup_audio_file(file_path: str):
    """Deletes the audio file from the server."""
    try:
        os.remove(file_path)
    except OSError as e:
        print(f"Error deleting file {file_path}: {e}") # Log error but don't fail the request


# --- API Endpoint ---
@app.post("/api/audit", summary="Process a call audio for quality audit", response_description="Returns the path to the generated PDF report")
async def audit_call(
    agent_name: Annotated[str, Form(..., description="Name of the agent")],
    call_id: Annotated[str, Form(..., description="Unique identifier for the call")],
    audio_file: Annotated[UploadFile, File(..., description="MP3 or WAV audio file of the call")],
    db: Session = Depends(get_db)
):
    """
    **Process a Call Quality Audit:**

    Upload an audio file (MP3/WAV) along with agent and call details to initiate a call quality audit.
    The system will:
    1. Save the audio file temporarily.
    2. Send the audio to Google Gemini 1.5 Pro for analysis, enforcing strict JSON output.
    3. Parse the AI's response, including error counts (NC, BC, EC), overall status (Pass/Fail),
       detailed scoring, and coaching summary.
    4. Store the audit results in an SQLite database.
    5. Generate a professional PDF report using Jinja2 and xhtml2pdf,
       incorporating a vibrant light theme and detailed sections.
    6. Automatically delete the uploaded audio file to prevent storage overflow.
    7. Return the file path to the generated PDF report for in-app download.

    **Note on EC (Extreme/Critical Errors):** If EC > 0, the call automatically fails.
    """
    
    # 1. Validate input data
    # Pydantic schemas can be used with Form/File directly, but here explicit conversion is fine
    audit_request_data = AuditRequest(agent_name=agent_name, call_id=call_id)

    # Check for existing call_id to prevent duplicates
    existing_audit = db.query(CallAudit).filter(CallAudit.call_id == audit_request_data.call_id).first()
    if existing_audit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Audit for call ID '{audit_request_data.call_id}' already exists. PDF path: {existing_audit.pdf_report_path}"
        )

    audio_file_path = None
    try:
        # 2. Save File
        audio_file_path = await save_upload_file(audio_file)

        # 3. Call Gemini API & Parse JSON
        gemini_response_data = await process_audio_with_gemini(audio_file_path)

        # 4. Save to SQLite
        current_datetime = datetime.utcnow()
        total_score_errors = gemini_response_data.NC + gemini_response_data.BC + gemini_response_data.EC # Sum of errors
        
        new_audit = CallAudit(
            agent_name=audit_request_data.agent_name,
            call_id=audit_request_data.call_id,
            evaluation_date=current_datetime,
            status=gemini_response_data.status,
            total_score=total_score_errors,
            pdf_report_path="" # Will be updated after PDF generation
        )
        db.add(new_audit)
        db.commit()
        db.refresh(new_audit) # Get the generated ID

        # 5. Generate PDF
        pdf_report_path = generate_pdf_report(
            audit_data=gemini_response_data,
            agent_name=audit_request_data.agent_name,
            call_id=audit_request_data.call_id,
            evaluation_date=current_datetime
        )

        # Update the database record with the PDF path
        new_audit.pdf_report_path = pdf_report_path
        db.add(new_audit)
        db.commit()
        db.refresh(new_audit)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Call audit processed successfully!",
                "audit_id": new_audit.id,
                "status": new_audit.status,
                "pdf_report_path": new_audit.pdf_report_path
            }
        )

    except HTTPException as e:
        raise e # Re-raise FastAPI HTTPExceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during the audit process: {e}"
        )
    finally:
        # 6. Delete Audio File (Auto-Cleanup)
        if audio_file_path and os.path.exists(audio_file_path):
            cleanup_audio_file(audio_file_path)


@app.get("/api/reports/{report_filename:path}", summary="Download a PDF audit report")
async def download_report(report_filename: str):
    """
    **Download PDF Audit Report:**

    Allows downloading of generated PDF audit reports using their filename.
    """
    file_path = os.path.join(settings.pdf_reports_dir, report_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return FileResponse(file_path, media_type="application/pdf", filename=report_filename)

@app.get("/api/audits/{call_id}", summary="Get audit details by Call ID")
async def get_audit_by_call_id(call_id: str, db: Session = Depends(get_db)):
    """
    **Get Audit Details by Call ID:**

    Retrieves the audit details for a specific `call_id`.
    """
    audit = db.query(CallAudit).filter(CallAudit.call_id == call_id).first()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Audit for call ID '{call_id}' not found")
    
    # Return a dictionary representation of the audit object
    return {
        "id": audit.id,
        "agent_name": audit.agent_name,
        "call_id": audit.call_id,
        "evaluation_date": audit.evaluation_date.isoformat(),
        "status": audit.status,
        "total_score": audit.total_score,
        "pdf_report_path": audit.pdf_report_path
    }

@app.get("/api/audits", summary="List all audits")
async def list_audits(db: Session = Depends(get_db)):
    """
    **List All Audits:**

    Retrieves a list of all performed call audits.
    """
    audits = db.query(CallAudit).all()
    return [
        {
            "id": audit.id,
            "agent_name": audit.agent_name,
            "call_id": audit.call_id,
            "evaluation_date": audit.evaluation_date.isoformat(),
            "status": audit.status,
            "total_score": audit.total_score,
            "pdf_report_path": audit.pdf_report_path
        }
        for audit in audits
    ]
