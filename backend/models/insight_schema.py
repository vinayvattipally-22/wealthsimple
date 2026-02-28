"""
Pydantic schema for a single insight — priority, category, headline, detail, value, etc.
"""
from typing import Optional
from pydantic import BaseModel


class InsightSchema(BaseModel):
    id: str
    priority: Optional[str] = None  # HIGH, MEDIUM, LOW
    category: Optional[str] = None  # ACT_NOW, THIS_YEAR, LONG_TERM
    headline: Optional[str] = None
    detail: Optional[str] = None
    estimated_value: Optional[float] = None
    calculation_shown: Optional[str] = None
    action_required: Optional[str] = None
    product_link: Optional[str] = None
    confidence: Optional[float] = None
    requires_additional_info: Optional[list[str]] = None


class InsightsSummary(BaseModel):
    total_identified_savings: Optional[float] = None
    act_now_count: int = 0
    this_year_count: int = 0
    long_term_count: int = 0
    requires_human_review: bool = False
    confidence_overall: Optional[float] = None


class InsightsResponse(BaseModel):
    insights: list[InsightSchema] = []
    summary: Optional[InsightsSummary] = None
