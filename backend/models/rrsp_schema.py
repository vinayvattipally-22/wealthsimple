"""
Pydantic schema for RRSP contribution receipt.
"""
from typing import Optional
from datetime import date
from pydantic import BaseModel


class RRSPReceiptFields(BaseModel):
    """RRSP receipt extracted fields."""
    contribution_amount: Optional[float] = None
    receipt_date: Optional[date] = None
    issuer: Optional[str] = None
    plan_type: Optional[str] = None  # e.g. RRSP, spousal
    tax_year: Optional[int] = None
