from pydantic import BaseModel, Field
from typing import List, Optional

# --- Gemini API Structured JSON schemas ---

class DetailedScoreItem(BaseModel):
    timestamp: str = Field(description="The timestamp of the call event, e.g., '0:45'")
    category: str = Field(description="The sub-category evaluated, e.g., 'Addressing Customer'")
    description: str = Field(description="Brief details of the action or infraction")
    pass_fail: str = Field(description="Evaluation status: 'Pass' or 'Fail'")

class GeminiAuditResult(BaseModel):
    NC: int = Field(description="Total count of Normal errors (Non-Critical compliance infractions)")
    BC: int = Field(description="Total count of Business Process compliance errors")
    EC: int = Field(description="Total count of Extreme/Critical compliance errors (Triggers auto-fail if > 0)")
    cc_score: int = Field(description="Calculated Customer Connection score (0 to 100)")
    bc_score: int = Field(description="Calculated Business Compliance score (0 to 100)")
    ec_score: int = Field(description="Calculated Execution Clarity score (0 to 100)")
    nc_score: int = Field(description="Calculated Next Steps score (0 to 100)")
    status: str = Field(description="Overall evaluation status: 'Pass' or 'Fail'")
    detailed_scoring: List[DetailedScoreItem] = Field(description="Timeline audit log of specific agent actions")
    coaching_summary: str = Field(description="Detailed coaching feedback and training instructions in English")

# --- FastAPI API response serialization schemas ---

class CallAuditBase(BaseModel):
    agent_name: str
    call_id: str
    evaluation_date: str
    status: str
    total_score: int
    pdf_report_path: str
    cc_score: int
    bc_score: int
    ec_score: int
    nc_score: int
    errors: str
    ai_feedback: str

class CallAuditResponse(CallAuditBase):
    id: int

    class Config:
        from_attributes = True  # Allows ORM models to convert to Pydantic automatically

class TrendItem(BaseModel):
    name: str
    score: int
    agent: str

class AgentRanking(BaseModel):
    name: str
    avgScore: int
    count: int

class StatsData(BaseModel):
    totalAudits: int
    passRate: str
    avgScore: int
    avgCC: int
    avgBC: int
    avgEC: int
    avgNC: int
    trends: List[TrendItem]
    agentRankings: List[AgentRanking]

class StatsResponse(BaseModel):
    success: bool
    data: StatsData
