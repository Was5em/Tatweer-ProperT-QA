import bcrypt
import pandas as pd
import streamlit as st
import os
import shutil
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import QAConfig
import traceback

Base = declarative_base()

db_import_error = None
engine = None
SessionLocal = None

def _make_engine():
    db_url = QAConfig.get_database_url()
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    return create_engine(db_url, connect_args=connect_args, pool_pre_ping=True, pool_recycle=1800)

try:
    engine = _make_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    db_import_error = traceback.format_exc()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)

class CallHistory(Base):
    __tablename__ = "call_history"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String)
    call_id = Column(String, unique=True, index=True)
    agent_name = Column(String)
    customer_name = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    patient_name = Column(String, nullable=True)
    patient_phone = Column(String, nullable=True)
    call_date = Column(String, nullable=True)
    transferred = Column(String)
    sale_closed = Column(String)
    score = Column(Integer)
    status = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    pdf_url = Column(String, nullable=True)
    
    # New campaign-specific fields
    campaign = Column(String, nullable=True)
    call_type = Column(String, nullable=True)
    fcr = Column(String, nullable=True)
    fcr_reason = Column(Text, nullable=True)
    customer_feedback = Column(String, nullable=True)
    customer_feedback_comment = Column(Text, nullable=True)
    bc_pct = Column(Float, default=100.0)
    ec_pct = Column(Float, default=100.0)
    cc_pct = Column(Float, default=100.0)
    nc_pct = Column(Float, default=100.0)

class AnalysisQueue(Base):
    __tablename__ = "analysis_queue"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    status = Column(String, default="Pending")
    result_json = Column(Text, nullable=True)
    error_msg = Column(String, nullable=True)
    created_at = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    call_id = Column(String, nullable=True, index=True)
    s3_key = Column(String, nullable=True)
    pdf_url = Column(String, nullable=True)

class UsageLog(Base):
    __tablename__ = "usage_log"
    date = Column(String, primary_key=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String)
    username = Column(String)
    action = Column(String)
    ip_address = Column(String)

class PromptConfig(Base):
    __tablename__ = "prompt_config"
    id = Column(Integer, primary_key=True, index=True)
    prompt_text = Column(Text, nullable=False)
    section_max = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(String)

class AuthManager:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def get_client_ip() -> str:
        try:
            headers = st.context.headers
            return headers.get("X-Forwarded-For", headers.get("Remote-Addr", "Unknown IP")).split(',')[0].strip()
        except Exception:
            return "Unknown IP"

    @staticmethod
    def sign_session(username: str, role: str, max_age: int = 30 * 24 * 60 * 60) -> str:
        import time
        secret = QAConfig.get_cookie_secret()
        expiry = int(time.time()) + max_age
        msg = f"{username}:{role}:{expiry}"
        sig = hmac.new(secret.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
        return f"{msg}:{sig}"

    @staticmethod
    def verify_session(token: str):
        if not token:
            return None, None
        parts = token.split(":")
        if len(parts) != 4:
            return None, None
        username, role, expiry_str, sig = parts
        try:
            expiry = int(expiry_str)
        except ValueError:
            return None, None
        
        import time
        if time.time() > expiry:
            return None, None
            
        secret = QAConfig.get_cookie_secret()
        expected_sig = hmac.new(secret.encode('utf-8'), f"{username}:{role}:{expiry_str}".encode('utf-8'), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return username, role
        return None, None

    @staticmethod
    def authenticate_by_username(username: str):
        """Resolves user metadata for active sessions."""
        if not username:
            return False, None
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == username).first()
            if user:
                return True, user.role
            return False, None

    @staticmethod
    def authenticate(username: str, password: str):
        with SessionLocal() as db:
            user = db.query(User).filter(User.username == username).first()
            if user and AuthManager.verify_password(password, user.password_hash):
                return True, user.role
            return False, None

class DataManager:
    @staticmethod
    def get_egypt_time():
        from datetime import datetime, timezone, timedelta
        try:
            import pytz
            cairo_tz = pytz.timezone("Africa/Cairo")
            return datetime.now(cairo_tz).replace(tzinfo=None)
        except Exception:
            return (datetime.now(timezone.utc) + timedelta(hours=3)).replace(tzinfo=None)

    @staticmethod
    def init_db(default_prompt=None, default_section_max=None):
        Base.metadata.create_all(bind=engine)

        with engine.connect() as conn:
            try:
                if "sqlite" in QAConfig.get_database_url():
                    result = conn.execute(text("PRAGMA table_info(call_history)"))
                    columns = [row[1] for row in result]
                else:
                    result = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name='call_history'"
                    ))
                    columns = [row[0] for row in result]

                if "patient_phone" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN patient_phone VARCHAR"))
                if "customer_name" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN customer_name VARCHAR"))
                if "customer_phone" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN customer_phone VARCHAR"))
                if "campaign" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN campaign VARCHAR"))
                if "call_type" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN call_type VARCHAR"))
                if "fcr" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN fcr VARCHAR"))
                if "fcr_reason" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN fcr_reason TEXT"))
                if "customer_feedback" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN customer_feedback VARCHAR"))
                if "customer_feedback_comment" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN customer_feedback_comment TEXT"))
                if "bc_pct" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN bc_pct FLOAT DEFAULT 100.0"))
                if "ec_pct" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN ec_pct FLOAT DEFAULT 100.0"))
                if "cc_pct" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN cc_pct FLOAT DEFAULT 100.0"))
                if "nc_pct" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN nc_pct FLOAT DEFAULT 100.0"))
                if "call_date" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN call_date VARCHAR"))
                if "input_tokens" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN input_tokens INTEGER DEFAULT 0"))
                if "output_tokens" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN output_tokens INTEGER DEFAULT 0"))
                if "cost" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN cost FLOAT DEFAULT 0.0"))
                if "pdf_url" not in columns:
                    conn.execute(text("ALTER TABLE call_history ADD COLUMN pdf_url VARCHAR"))
                conn.commit()

                if "sqlite" in QAConfig.get_database_url():
                    result_q = conn.execute(text("PRAGMA table_info(analysis_queue)"))
                    columns_q = [row[1] for row in result_q]
                else:
                    result_q = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name='analysis_queue'"
                    ))
                    columns_q = [row[0] for row in result_q]

                if "input_tokens" not in columns_q:
                    conn.execute(text("ALTER TABLE analysis_queue ADD COLUMN input_tokens INTEGER DEFAULT 0"))
                if "output_tokens" not in columns_q:
                    conn.execute(text("ALTER TABLE analysis_queue ADD COLUMN output_tokens INTEGER DEFAULT 0"))
                if "cost" not in columns_q:
                    conn.execute(text("ALTER TABLE analysis_queue ADD COLUMN cost FLOAT DEFAULT 0.0"))
                if "call_id" not in columns_q:
                    conn.execute(text("ALTER TABLE analysis_queue ADD COLUMN call_id VARCHAR"))
                if "s3_key" not in columns_q:
                    conn.execute(text("ALTER TABLE analysis_queue ADD COLUMN s3_key VARCHAR"))
                if "pdf_url" not in columns_q:
                    conn.execute(text("ALTER TABLE analysis_queue ADD COLUMN pdf_url VARCHAR"))
                conn.commit()
            except Exception as e:
                print(f"Migration warning: {e}")

        with SessionLocal() as db:
            try:
                stuck_items = db.query(AnalysisQueue).filter(
                    AnalysisQueue.status.in_(["Pending", "Processing"])
                ).all()
                for item in stuck_items:
                    item.status = "Failed"
                    item.error_msg = "Interrupted due to server restart."
                if stuck_items:
                    db.commit()
            except Exception as e:
                print(f"Stuck task reset error: {e}")

        temp_dir = "./temp_uploads"
        try:
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path}. Reason: {e}")
            else:
                os.makedirs(temp_dir, exist_ok=True)
        except Exception as e:
            print(f"Temp folder cleanup error: {e}")

        if default_prompt and default_section_max:
            with SessionLocal() as db:
                try:
                    import json
                    active_prompt = db.query(PromptConfig).filter(PromptConfig.is_active == True).first()
                    if not active_prompt:
                        db.add(PromptConfig(
                            prompt_text = default_prompt,
                            section_max = json.dumps(default_section_max),
                            is_active   = True,
                            updated_at  = DataManager.get_egypt_time().strftime("%Y-%m-%d %H:%M:%S")
                        ))
                    else:
                        active_prompt.prompt_text = default_prompt
                        active_prompt.section_max = json.dumps(default_section_max)
                        active_prompt.updated_at  = DataManager.get_egypt_time().strftime("%Y-%m-%d %H:%M:%S")
                    db.commit()
                except Exception as e:
                    print(f"Prompt seeding error: {e}")

        with SessionLocal() as db:
            admin_user = db.query(User).filter(User.username == QAConfig.get_admin_user()).first()
            if not admin_user:
                db.add(User(
                    username      = QAConfig.get_admin_user(),
                    password_hash = AuthManager.hash_password(QAConfig.get_admin_pass()),
                    role          = "admin"
                ))
            else:
                if not AuthManager.verify_password(QAConfig.get_admin_pass(), admin_user.password_hash):
                    admin_user.password_hash = AuthManager.hash_password(QAConfig.get_admin_pass())

            auditor_user = db.query(User).filter(User.username == QAConfig.get_auditor_user()).first()
            if not auditor_user:
                db.add(User(
                    username      = QAConfig.get_auditor_user(),
                    password_hash = AuthManager.hash_password(QAConfig.get_auditor_pass()),
                    role          = "user"
                ))
            else:
                if not AuthManager.verify_password(QAConfig.get_auditor_pass(), auditor_user.password_hash):
                    auditor_user.password_hash = AuthManager.hash_password(QAConfig.get_auditor_pass())
            db.commit()

    @staticmethod
    def log_activity(username: str, action: str):
        with SessionLocal() as db:
            db.add(ActivityLog(
                timestamp  = DataManager.get_egypt_time().strftime("%Y-%m-%d %H:%M:%S"),
                username   = username,
                action     = action,
                ip_address = AuthManager.get_client_ip()
            ))
            db.commit()

    @staticmethod
    def log_usage(prompt_tokens: int, response_tokens: int):
        today = DataManager.get_egypt_time().strftime("%Y-%m-%d")
        cost  = QAConfig.calculate_cost(prompt_tokens, response_tokens)
        with SessionLocal() as db:
            log = db.query(UsageLog).filter(UsageLog.date == today).first()
            if log:
                log.input_tokens  += prompt_tokens
                log.output_tokens += response_tokens
                log.total_cost    += cost
            else:
                db.add(UsageLog(date=today, input_tokens=prompt_tokens,
                                output_tokens=response_tokens, total_cost=cost))
            db.commit()

    @staticmethod
    def add_to_queue(filename: str, s3_key: str = None) -> int:
        with SessionLocal() as db:
            item = AnalysisQueue(
                filename=filename,
                s3_key=s3_key,
                created_at=DataManager.get_egypt_time().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.add(item)
            db.commit()
            return item.id

    @staticmethod
    def update_queue_status(item_id: int, status: str, result=None, error=None, input_tokens=0, output_tokens=0, cost=0.0):
        with SessionLocal() as db:
            item = db.query(AnalysisQueue).filter(AnalysisQueue.id == item_id).first()
            if item:
                item.status = status
                if result is not None:
                    item.result_json   = result
                    item.input_tokens  = input_tokens
                    item.output_tokens = output_tokens
                    item.cost          = cost
                if error:  item.error_msg  = error
                db.commit()

    @staticmethod
    def save_call_to_history(call_data: Dict[str, Any]):
        with SessionLocal() as db:
            call_id  = call_data.get("Call_ID", "N/A")
            existing = db.query(CallHistory).filter(CallHistory.call_id == call_id).first()
            
            c_name = call_data.get("Customer_Name", call_data.get("Patient_Name", "N/A"))
            c_phone = call_data.get("Customer_Phone", call_data.get("Patient_Phone", "N/A"))
            
            call_info = {
                "timestamp":                 DataManager.get_egypt_time().strftime("%Y-%m-%d %H:%M"),
                "agent_name":                call_data.get("Agent_Name", "N/A"),
                "customer_name":             c_name,
                "customer_phone":            c_phone,
                "patient_name":              c_name, # backward compatibility fallback
                "patient_phone":             c_phone, # backward compatibility fallback
                "call_date":                 call_data.get("Call_Date", "N/A"),
                "transferred":               call_data.get("Compliance_Checklist", {}).get("Call_Transferred", "No"),
                "sale_closed":               call_data.get("Compliance_Checklist", {}).get("Sale_Closed", "No"),
                "score":                     call_data.get("Score", 0),
                "status":                    call_data.get("Call_Status", "N/A"),
                "input_tokens":              call_data.get("_tokens_input", 0),
                "output_tokens":             call_data.get("_tokens_output", 0),
                "cost":                      call_data.get("_cost", 0.0),
                "pdf_url":                   call_data.get("pdf_url", None),
                
                # New fields mapping
                "campaign":                  call_data.get("Campaign", "Tatweer Misr"),
                "call_type":                 call_data.get("Call_Type", "General Inquiry"),
                "fcr":                       call_data.get("FCR", "NA"),
                "fcr_reason":                call_data.get("FCR_Reason", ""),
                "customer_feedback":         call_data.get("Customer_Feedback", "NA"),
                "customer_feedback_comment": call_data.get("Customer_Feedback_Comment", ""),
                "bc_pct":                    call_data.get("bc_pct", 100.0),
                "ec_pct":                    call_data.get("ec_pct", 100.0),
                "cc_pct":                    call_data.get("cc_pct", 100.0),
                "nc_pct":                    call_data.get("nc_pct", 100.0),
            }
            if existing:
                for k, v in call_info.items():
                    setattr(existing, k, v)
            else:
                db.add(CallHistory(call_id=call_id, **call_info))
            db.commit()
        DataManager.get_all_history.clear()

    @staticmethod
    def link_queue_to_call(queue_item_id: int, call_id: str, pdf_url: str = None):
        with SessionLocal() as db:
            item = db.query(AnalysisQueue).filter(AnalysisQueue.id == queue_item_id).first()
            if item:
                item.call_id = call_id
                if pdf_url:
                    item.pdf_url = pdf_url
                db.commit()

    @staticmethod
    def update_call_history(call_id: str, updated_data: dict) -> bool:
        with SessionLocal() as db:
            call = db.query(CallHistory).filter(CallHistory.call_id == call_id).first()
            if call:
                for k, v in updated_data.items():
                    setattr(call, k, v)
                
                queue_item = db.query(AnalysisQueue).filter(AnalysisQueue.call_id == call_id).first()
                if queue_item and queue_item.result_json:
                    import json
                    try:
                        res = json.loads(queue_item.result_json)
                        if "agent_name" in updated_data:
                            res["Agent_Name"] = updated_data["agent_name"]
                        if "score" in updated_data:
                            res["Score"] = int(updated_data["score"])
                        if "status" in updated_data:
                            res["Call_Status"] = updated_data["status"]
                        queue_item.result_json = json.dumps(res)
                    except Exception as err:
                        print(f"Sync edit to result_json error: {err}")
                
                db.commit()
                DataManager.get_all_history.clear()
                return True
            return False

    @staticmethod
    def delete_call_history(call_id: str) -> bool:
        with SessionLocal() as db:
            call = db.query(CallHistory).filter(CallHistory.call_id == call_id).first()
            if call:
                db.delete(call)
                queue_item = db.query(AnalysisQueue).filter(AnalysisQueue.call_id == call_id).first()
                if queue_item:
                    queue_item.call_id = None
                db.commit()
                DataManager.get_all_history.clear()
                return True
            return False

    @staticmethod
    @st.cache_data(ttl=30, show_spinner=False)
    def get_all_history() -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql_query("SELECT * FROM call_history", conn)

    @staticmethod
    def get_activity_logs() -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql_query("SELECT * FROM activity_logs ORDER BY id DESC", conn)

    @staticmethod
    def get_active_prompt_config() -> Dict[str, Any]:
        """Retrieves active scorecard prompt and weights from DB or falls back to system defaults."""
        try:
            with SessionLocal() as db:
                config = db.query(PromptConfig).filter(PromptConfig.is_active == True).first()
                if config:
                    import json
                    return {
                        "prompt_text": config.prompt_text,
                        "section_max": json.loads(config.section_max)
                    }
        except Exception as e:
            print(f"Error loading prompt config from DB: {e}")
        
        try:
            from core import OFFICIAL_SCORECARD_PROMPT, SECTION_MAX
            return {
                "prompt_text": OFFICIAL_SCORECARD_PROMPT,
                "section_max": SECTION_MAX
            }
        except Exception as e:
            print(f"Fallback loading error: {e}")
            return {
                "prompt_text": "",
                "section_max": {}
            }

    @staticmethod
    def save_prompt_config(prompt_text: str, section_max: dict) -> bool:
        """Stores new scorecard configuration and deactivates prior configs."""
        try:
            import json
            with SessionLocal() as db:
                db.query(PromptConfig).update({PromptConfig.is_active: False})
                db.add(PromptConfig(
                    prompt_text = prompt_text,
                    section_max = json.dumps(section_max),
                    is_active   = True,
                    updated_at  = DataManager.get_egypt_time().strftime("%Y-%m-%d %H:%M:%S")
                ))
                db.commit()
                return True
        except Exception as e:
            print(f"Error saving prompt config to DB: {e}")
            return False
