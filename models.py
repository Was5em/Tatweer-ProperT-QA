from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class CallAudit(Base):
    __tablename__ = "call_audits"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, index=True)
    call_id = Column(String, unique=True, index=True)
    evaluation_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String) # "Pass" or "Fail"
    total_score = Column(Integer) # Sum of errors (NC+BC+EC)
    pdf_report_path = Column(String)
