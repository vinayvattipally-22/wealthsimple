"""
Pydantic schema for advisor review case.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from models.insight_schema import InsightSchema


class CaseSchema(BaseModel):
    profile_id: int
    case_id: Optional[int] = None
    insights: list[InsightSchema] = []
    review_status: str = "PENDING"  # PENDING, APPROVED, REJECTED, ESCALATED
    advisor_id: Optional[int] = None
    flags: Optional[list[str]] = None
    confidence_score: Optional[float] = None
    sla_due_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
