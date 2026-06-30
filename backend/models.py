from sqlalchemy import Column, Integer, String, Text
from database import Base

class CallAudit(Base):
    __tablename__ = "call_audits"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, index=True, nullable=False)
    call_id = Column(String, unique=True, index=True, nullable=False)
    evaluation_date = Column(String, nullable=False)
    status = Column(String, nullable=False)  # "Pass" or "Fail"
    total_score = Column(Integer, nullable=False)  # e.g. 85
    pdf_report_path = Column(String, nullable=False)
    
    # Detailed sub-scores for statistics calculations
    cc_score = Column(Integer, default=0)
    bc_score = Column(Integer, default=0)
    ec_score = Column(Integer, default=0)
    nc_score = Column(Integer, default=0)
    
    errors = Column(Text, default="")
    ai_feedback = Column(Text, default="")
