from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

# Pydantic schema for the detailed_scoring item within Gemini's response
class DetailedScoringItem(BaseModel):
    timestamp: str = Field(..., description="Timestamp of the event in the call")
    category: str = Field(..., description="Category of the action or event")
    description: str = Field(..., description="Description of the action or event")
    pass_fail: Literal["Pass", "Fail"] = Field(..., description="Whether the item passed or failed")

# Pydantic schema for the expected strict JSON output from Gemini
class GeminiAuditResponse(BaseModel):
    NC: int = Field(..., description="Normal Errors count")
    BC: int = Field(..., description="Business Process Errors count")
    EC: int = Field(..., description="Extreme/Critical Errors count, triggers auto-fail")
    status: Literal["Pass", "Fail"] = Field(..., description="Overall call audit status")
    detailed_scoring: List[DetailedScoringItem] = Field(..., description="Array of detailed scoring items")
    coaching_summary: str = Field(..., description="Final auditor summary for coaching")

# Pydantic schema for the FastAPI form data input
class AuditRequest(BaseModel):
    agent_name: str
    call_id: str
