"""
PIPEDA-compliant audit logging: every data access and review decision with timestamp, user_id, purpose.
Immutable audit trail.
"""
from datetime import datetime
from typing import Optional, Any


async def log_access(
    user_id: Optional[int],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    purpose: Optional[str] = None,
    details: Optional[dict] = None,
    db_session=None,
):
    """Log a data access or action for audit trail."""
    if db_session is None:
        return
    from database.models import AuditLog
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        purpose=purpose,
        details=details,
    )
    db_session.add(entry)
    await db_session.flush()


async def log_review_decision(
    case_id: int,
    advisor_id: Optional[int],
    decision: str,  # APPROVE, REJECT, MODIFY, ESCALATE
    details: Optional[dict] = None,
    db_session=None,
):
    """Log advisor review decision."""
    await log_access(
        user_id=advisor_id,
        action=f"REVIEW_{decision}",
        resource_type="review_case",
        resource_id=str(case_id),
        purpose="advisor_review",
        details=details,
        db_session=db_session,
    )
