"""Advisor review queue: list cases, case detail, approve/reject/modify/escalate, comment.
Also: stock insight review endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.session import get_db
from database.models import FinancialProfile, Insight, ReviewCase, AuditLog, User, StockInsight, StockNews, Document

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


def _insight_to_dict(i: Insight) -> dict:
    return {
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
        "advisor_comment": i.advisor_comment,
        "advisor_id": i.advisor_id,
        "reviewed_at": i.reviewed_at.isoformat() if i.reviewed_at else None,
    }


@router.get("/queue")
async def get_queue(
    limit: int = 50,
    offset: int = 0,
    status: str = "PENDING",
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """List review cases, paginated, sorted by SLA. Filter by status (default PENDING)."""
    valid_statuses = ["PENDING", "APPROVED", "REJECTED", "ESCALATED", "ALL"]
    if status not in valid_statuses:
        status = "PENDING"

    query = (
        select(ReviewCase, FinancialProfile)
        .join(FinancialProfile, ReviewCase.profile_id == FinancialProfile.id)
        .order_by(ReviewCase.sla_due_at.asc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    if status != "ALL":
        query = query.where(ReviewCase.status == status)

    result = await db.execute(query)
    rows = result.all()

    # Get insight counts per profile
    profile_ids = [case.profile_id for case, _ in rows]
    counts = {}
    if profile_ids:
        count_result = await db.execute(
            select(Insight.profile_id, func.count(Insight.id))
            .where(Insight.profile_id.in_(profile_ids))
            .group_by(Insight.profile_id)
        )
        counts = dict(count_result.all())

    cases = []
    for case, profile in rows:
        employment = (profile.profile_data or {}).get("employment", {})
        # Get user info
        user = await db.get(User, profile.user_id) if profile.user_id else None
        cases.append({
            "case_id": case.id,
            "profile_id": case.profile_id,
            "status": case.status,
            "confidence_score": case.confidence_score,
            "sla_due_at": case.sla_due_at.isoformat() if case.sla_due_at else None,
            "flags": case.flags or [],
            "income": employment.get("total_employment_income"),
            "province": profile.province_code,
            "tax_year": profile.tax_year,
            "user_name": user.name if user else None,
            "user_email": user.email if user else None,
            "insight_count": counts.get(case.profile_id, 0),
            "created_at": case.created_at.isoformat() if case.created_at else None,
        })
    return {"queue": cases, "total": len(cases)}


@router.get("/case/{case_id}")
async def get_case(case_id: int, advisor: User = Depends(require_advisor), db: AsyncSession = Depends(get_db)):
    """Full case detail with insights, profile data, and user info."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    profile = await db.get(FinancialProfile, case.profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    user = await db.get(User, profile.user_id) if profile.user_id else None

    result = await db.execute(select(Insight).where(Insight.profile_id == case.profile_id))
    insights = result.scalars().all()

    # Get linked documents for this profile
    doc_result = await db.execute(
        select(Document).where(Document.profile_id == case.profile_id)
    )
    documents = doc_result.scalars().all()

    employment = (profile.profile_data or {}).get("employment", {})
    derived = (profile.profile_data or {}).get("derived", {})
    registered = (profile.profile_data or {}).get("registered_accounts", {})

    return {
        "case_id": case.id,
        "profile_id": case.profile_id,
        "status": case.status,
        "confidence_score": case.confidence_score,
        "flags": case.flags or [],
        "sla_due_at": case.sla_due_at.isoformat() if case.sla_due_at else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "tax_year": profile.tax_year,
        "province": profile.province_code,
        "user_name": user.name if user else None,
        "user_email": user.email if user else None,
        "documents": [
            {
                "id": d.id,
                "file_name": d.file_name,
                "doc_type": d.doc_type,
                "has_redacted_pdf": bool(d.redacted_file_data),
            }
            for d in documents
        ],
        "profile_summary": {
            "income": employment.get("total_employment_income", 0),
            "tax_withheld": employment.get("total_income_tax_withheld", 0),
            "cpp": employment.get("total_cpp_contributions", 0),
            "ei": employment.get("total_ei_premiums", 0),
            "tax_liability": derived.get("estimated_tax_liability"),
            "marginal_rate": derived.get("marginal_rate_combined"),
            "rrsp_room": registered.get("rrsp_room_remaining"),
            "tfsa_room": registered.get("tfsa_room_remaining"),
        },
        "insights": [_insight_to_dict(i) for i in insights],
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
        select(Insight).where(Insight.profile_id == case.profile_id)
    )
    insights = result.scalars().all()
    now = datetime.utcnow()
    for i in insights:
        if insight_ids is None or i.id in (insight_ids or []):
            i.review_status = "APPROVED"
            i.advisor_id = advisor.id
            i.reviewed_at = now
    case.status = "APPROVED"
    case.advisor_id = advisor.id
    profile = await db.get(FinancialProfile, case.profile_id)
    if profile:
        profile.review_status = "APPROVED"
        profile.approved_at = now
        profile.advisor_id = advisor.id
    await log_review_decision(case_id, advisor.id, "APPROVE", body, db)
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
    case.advisor_id = advisor.id
    # If there's a reason, store it on each insight
    reason = (body or {}).get("reason", "")
    if reason:
        result = await db.execute(select(Insight).where(Insight.profile_id == case.profile_id))
        for ins in result.scalars().all():
            ins.review_status = "REJECTED"
            ins.advisor_comment = reason
            ins.advisor_id = advisor.id
            ins.reviewed_at = datetime.utcnow()
    await log_review_decision(case_id, advisor.id, "REJECT", body, db)
    await db.commit()
    return {"case_id": case_id, "status": "REJECTED"}


@router.post("/case/{case_id}/comment")
async def comment_insight(
    case_id: int,
    body: dict = Body(...),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Add advisor comment/feedback on a specific insight.
    body: {"insight_id": 1, "comment": "Good analysis but value seems high"}
    """
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    insight_id = body.get("insight_id")
    comment = (body.get("comment") or "").strip()
    if not insight_id:
        raise HTTPException(400, "insight_id is required")

    ins = await db.get(Insight, insight_id)
    if not ins or ins.profile_id != case.profile_id:
        raise HTTPException(404, "Insight not found in this case")

    ins.advisor_comment = comment
    ins.advisor_id = advisor.id
    ins.reviewed_at = datetime.utcnow()

    await log_review_decision(case_id, advisor.id, "COMMENT", body, db)
    await db.commit()
    return {"insight_id": insight_id, "comment": comment, "status": "saved"}


@router.post("/case/{case_id}/insight/{insight_id}/approve")
async def approve_insight(
    case_id: int,
    insight_id: int,
    body: dict = Body(default=None),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Approve a single insight with optional comment."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    ins = await db.get(Insight, insight_id)
    if not ins or ins.profile_id != case.profile_id:
        raise HTTPException(404, "Insight not found in this case")

    ins.review_status = "APPROVED"
    ins.advisor_id = advisor.id
    ins.reviewed_at = datetime.utcnow()
    comment = ((body or {}).get("comment") or "").strip()
    if comment:
        ins.advisor_comment = comment

    # Check if all insights are now reviewed
    result = await db.execute(
        select(Insight).where(
            Insight.profile_id == case.profile_id,
            Insight.review_status == "PENDING",
        )
    )
    remaining = result.scalars().all()
    # Don't count the one we just approved
    remaining = [r for r in remaining if r.id != insight_id]

    await log_review_decision(case_id, advisor.id, "APPROVE_INSIGHT", {"insight_id": insight_id, **(body or {})}, db)
    await db.commit()
    return {"insight_id": insight_id, "status": "APPROVED", "remaining_pending": len(remaining)}


@router.post("/case/{case_id}/insight/{insight_id}/reject")
async def reject_insight(
    case_id: int,
    insight_id: int,
    body: dict = Body(default=None),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Reject a single insight with optional comment."""
    case = await db.get(ReviewCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    ins = await db.get(Insight, insight_id)
    if not ins or ins.profile_id != case.profile_id:
        raise HTTPException(404, "Insight not found in this case")

    ins.review_status = "REJECTED"
    ins.advisor_id = advisor.id
    ins.reviewed_at = datetime.utcnow()
    comment = ((body or {}).get("comment") or "").strip()
    if comment:
        ins.advisor_comment = comment

    await log_review_decision(case_id, advisor.id, "REJECT_INSIGHT", {"insight_id": insight_id, **(body or {})}, db)
    await db.commit()
    return {"insight_id": insight_id, "status": "REJECTED"}


@router.post("/case/{case_id}/modify")
async def modify_case(
    case_id: int,
    body: dict = Body(...),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Modify insight(s) before approval."""
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
        if "comment" in mod:
            ins.advisor_comment = mod["comment"]
        ins.advisor_id = advisor.id
        ins.reviewed_at = datetime.utcnow()
    await log_review_decision(case_id, advisor.id, "MODIFY", body, db)
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
    case.advisor_id = advisor.id
    await log_review_decision(case_id, advisor.id, "ESCALATE", body, db)
    await db.commit()
    return {"case_id": case_id, "status": "ESCALATED"}


# ── Stock Insight Review Endpoints ──


@router.get("/stock-queue")
async def get_stock_queue(
    status: str = Query(default="PENDING"),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """List stock insights grouped by ticker for advisor review."""
    valid = ["PENDING", "APPROVED", "REJECTED", "ALL"]
    if status not in valid:
        status = "PENDING"

    query = select(StockInsight).order_by(StockInsight.created_at.desc())
    if status != "ALL":
        query = query.where(StockInsight.review_status == status)

    result = await db.execute(query)
    insights = result.scalars().all()

    # Group by ticker
    grouped = {}
    for ins in insights:
        key = ins.ticker
        if key not in grouped:
            grouped[key] = {
                "ticker": ins.ticker,
                "company_name": ins.company_name,
                "insights": [],
                "pending_count": 0,
                "total_count": 0,
            }
        grouped[key]["insights"].append({
            "id": ins.id,
            "timeframe": ins.timeframe,
            "direction": ins.direction,
            "confidence": ins.confidence,
            "reasoning": ins.reasoning,
            "review_status": ins.review_status,
            "advisor_comment": ins.advisor_comment,
            "reviewed_at": ins.reviewed_at.isoformat() if ins.reviewed_at else None,
            "created_at": ins.created_at.isoformat() if ins.created_at else None,
        })
        grouped[key]["total_count"] += 1
        if ins.review_status == "PENDING":
            grouped[key]["pending_count"] += 1

    # Fetch referenced news for each insight
    all_article_ids = set()
    for ins in insights:
        for aid in (ins.news_article_ids or []):
            all_article_ids.add(aid)

    articles_map = {}
    if all_article_ids:
        art_result = await db.execute(
            select(StockNews).where(StockNews.id.in_(all_article_ids))
        )
        for a in art_result.scalars().all():
            articles_map[a.id] = {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "publisher": a.publisher,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }

    # Attach referenced articles to each insight
    for ins in insights:
        ticker_group = grouped.get(ins.ticker)
        if not ticker_group:
            continue
        for insight_dict in ticker_group["insights"]:
            if insight_dict["id"] == ins.id:
                insight_dict["referenced_articles"] = [
                    articles_map[aid]
                    for aid in (ins.news_article_ids or [])
                    if aid in articles_map
                ]

    return {"queue": list(grouped.values())}


@router.post("/stock-insight/{insight_id}/approve")
async def approve_stock_insight(
    insight_id: int,
    body: dict = Body(default=None),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Approve a single stock insight."""
    ins = await db.get(StockInsight, insight_id)
    if not ins:
        raise HTTPException(404, "Stock insight not found")

    ins.review_status = "APPROVED"
    ins.advisor_id = advisor.id
    ins.reviewed_at = datetime.utcnow()
    comment = ((body or {}).get("comment") or "").strip()
    if comment:
        ins.advisor_comment = comment

    await db.commit()
    return {"insight_id": insight_id, "status": "APPROVED"}


@router.post("/stock-insight/{insight_id}/reject")
async def reject_stock_insight(
    insight_id: int,
    body: dict = Body(default=None),
    advisor: User = Depends(require_advisor),
    db: AsyncSession = Depends(get_db),
):
    """Reject a single stock insight."""
    ins = await db.get(StockInsight, insight_id)
    if not ins:
        raise HTTPException(404, "Stock insight not found")

    ins.review_status = "REJECTED"
    ins.advisor_id = advisor.id
    ins.reviewed_at = datetime.utcnow()
    comment = ((body or {}).get("comment") or "").strip()
    if comment:
        ins.advisor_comment = comment

    await db.commit()
    return {"insight_id": insight_id, "status": "REJECTED"}
