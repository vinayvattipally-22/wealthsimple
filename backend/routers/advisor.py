"""Advisor review queue: list cases, case detail, approve/reject/modify/escalate."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.models import FinancialProfile, Insight, ReviewCase, AuditLog, User

from services.audit_service import log_review_decision
from middleware.auth import require_advisor

router = APIRouter()

# Review rules (Phase 7)
AUTO_APPROVE_MIN_CONFIDENCE = 0.85
AUTO_APPROVE_MAX_VALUE = 50_000.00
MANDATORY_HUMAN_REVIEW_FLAGS = [
    "TAX_RATE_ANOMALY", "INCOME_DISCREPANCY", "CPP_EXCEEDS_MAXIMUM",
    "HIGH_VALUE_INSIGHT", "NEAR_RETIREMENT", "MULTI_EMPLOYER_COMPLEX",
]


@router.get("/queue")
async def get_queue(
    limit: int = 50,
    offset: int = 0,
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """List pending review cases, paginated, sorted by SLA."""
    result = await db.execute(
        select(ReviewCase, FinancialProfile)
        .join(FinancialProfile, ReviewCase.profile_id == FinancialProfile.id)
        .where(ReviewCase.status == "PENDING")
        .order_by(ReviewCase.sla_due_at.asc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    cases = []
    for case, profile in rows:
        employment = (profile.profile_data or {}).get("employment", {})
        cases.append({
            "case_id": case.id,
            "profile_id": case.profile_id,
            "status": case.status,
            "confidence_score": case.confidence_score,
            "sla_due_at": case.sla_due_at.isoformat() if case.sla_due_at else None,
            "flags": case.flags or [],
            "income": employment.get("total_employment_income"),
            "province": profile.province_code,
            "insight_count": 0,  # can be filled with a count query
        })
    return {"queue": cases, "total": len(cases)}


@router.get("/case/{case_id}")
async def get_case(case_id: int, advisor: User = Depends(require_advisor), db: AsyncSession = Depends(get_db)):
    """Full case detail with insights and confidence."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    profile = await db.get(FinancialProfile, case.profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    result = await db.execute(select(Insight).where(Insight.profile_id == case.profile_id))
    insights = result.scalars().all()
    return {
        "case_id": case.id,
        "profile_id": case.profile_id,
        "status": case.status,
        "confidence_score": case.confidence_score,
        "flags": case.flags or [],
        "sla_due_at": case.sla_due_at.isoformat() if case.sla_due_at else None,
        "profile": profile.profile_data,
        "insights": [
            {
                "id": i.id,
                "insight_type": i.insight_type,
                "priority": i.priority,
                "category": i.category,
                "headline": i.headline,
                "detail": i.detail,
                "estimated_value": i.estimated_value,
                "calculation_shown": i.calculation_shown,
                "action_required": i.action_required,
                "product_link": i.product_link,
                "confidence": i.confidence,
                "review_status": i.review_status,
            }
            for i in insights
        ],
    }


@router.post("/case/{case_id}/approve")
async def approve_case(
    case_id: int,
    body: dict = Body(default=None),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Approve all or selected insights. body: {} or {"insight_ids": [1,2,3]}."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    insight_ids = (body or {}).get("insight_ids")
    result = await db.execute(
        select(Insight).where(
            Insight.profile_id == case.profile_id,
            Insight.review_status == "PENDING",
        )
    )
    insights = result.scalars().all()
    for i in insights:
        if insight_ids is None or i.id in (insight_ids or []):
            i.review_status = "APPROVED"
    case.status = "APPROVED"
    case.advisor_id = (body or {}).get("advisor_id")
    profile = await db.get(FinancialProfile, case.profile_id)
    if profile:
        profile.review_status = "APPROVED"
        profile.approved_at = datetime.utcnow()
    await log_review_decision(case_id, (body or {}).get("advisor_id"), "APPROVE", body, db)
    await db.commit()
    return {"case_id": case_id, "status": "APPROVED"}


@router.post("/case/{case_id}/reject")
async def reject_case(
    case_id: int,
    body: dict = Body(default=None),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Reject case with optional reason."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    case.status = "REJECTED"
    case.advisor_id = (body or {}).get("advisor_id")
    await log_review_decision(case_id, (body or {}).get("advisor_id"), "REJECT", body, db)
    await db.commit()
    return {"case_id": case_id, "status": "REJECTED"}


@router.post("/case/{case_id}/modify")
async def modify_case(
    case_id: int,
    body: dict = Body(...),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Modify insight(s) before approval. body: {"insight_id": 1, "headline": "...", "estimated_value": 1000} or list of such."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    modifications = body.get("modifications", [body])
    if not isinstance(modifications, list):
        modifications = [modifications]
    for mod in modifications:
        iid = mod.get("insight_id")
        if iid is None:
            continue
        ins = await db.get(Insight, iid)
        if not ins or ins.profile_id != case.profile_id:
            continue
        if "headline" in mod:
            ins.headline = mod["headline"]
        if "detail" in mod:
            ins.detail = mod["detail"]
        if "estimated_value" in mod:
            ins.estimated_value = mod["estimated_value"]
        if "action_required" in mod:
            ins.action_required = mod["action_required"]
    await log_review_decision(case_id, body.get("advisor_id"), "MODIFY", body, db)
    await db.commit()
    return {"case_id": case_id, "status": "MODIFIED"}


@router.post("/case/{case_id}/escalate")
async def escalate_case(
    case_id: int,
    body: dict = Body(default=None),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Escalate to senior advisor."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    case.status = "ESCALATED"
    case.advisor_id = (body or {}).get("advisor_id")
    await log_review_decision(case_id, (body or {}).get("advisor_id"), "ESCALATE", body, db)
    await db.commit()
    return {"case_id": case_id, "status": "ESCALATED"}
