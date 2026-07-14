"""User-specific endpoints: document history, profile summary, dashboard, advisor."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.session import get_db
from database.models import User, Document, FinancialProfile, Insight, ActionItem
from middleware.auth import get_current_user
from middleware.rate_limiter import limiter, READ_LIMIT
from services.advisor_service import build_advisor_data

router = APIRouter()


@router.get("/documents")
@limiter.limit(READ_LIMIT)
async def list_user_documents(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all documents + linked profiles + insight counts for the current user."""
    # Query documents belonging to this user
    doc_result = await db.execute(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    )
    documents = doc_result.scalars().all()

    # Query all profiles belonging to this user
    profile_result = await db.execute(
        select(FinancialProfile).where(FinancialProfile.user_id == user.id)
    )
    profiles = {p.id: p for p in profile_result.scalars().all()}

    # Query insight counts and total savings per profile
    profile_ids = list(profiles.keys())
    insight_stats = {}
    if profile_ids:
        insight_result = await db.execute(
            select(
                Insight.profile_id,
                func.count(Insight.id).label("insight_count"),
                func.coalesce(func.sum(Insight.estimated_value), 0).label("total_savings"),
            )
            .where(Insight.profile_id.in_(profile_ids))
            .group_by(Insight.profile_id)
        )
        insight_stats = {
            row.profile_id: {"count": row.insight_count, "savings": float(row.total_savings)}
            for row in insight_result
        }

    items = []
    linked_profile_ids = set()

    for doc in documents:
        profile = profiles.get(doc.profile_id)
        stats = insight_stats.get(doc.profile_id, {"count": 0, "savings": 0}) if doc.profile_id else {"count": 0, "savings": 0}
        if doc.profile_id:
            linked_profile_ids.add(doc.profile_id)
        items.append({
            "document_id": doc.id,
            "file_name": doc.file_name,
            "doc_type": doc.doc_type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "profile_id": doc.profile_id,
            "tax_year": profile.tax_year if profile else None,
            "province": profile.province_code if profile else None,
            "review_status": profile.review_status if profile else None,
            "insights_count": stats["count"],
            "total_savings": round(stats["savings"], 2),
        })

    # Include profiles without linked documents
    for pid, profile in profiles.items():
        if pid not in linked_profile_ids:
            stats = insight_stats.get(pid, {"count": 0, "savings": 0})
            items.append({
                "document_id": None,
                "file_name": None,
                "doc_type": None,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "profile_id": pid,
                "tax_year": profile.tax_year,
                "province": profile.province_code,
                "review_status": profile.review_status,
                "insights_count": stats["count"],
                "total_savings": round(stats["savings"], 2),
            })

    return {"documents": items, "user_name": user.name, "user_email": user.email}


@router.get("/dashboard")
@limiter.limit(READ_LIMIT)
async def user_dashboard(
    request: Request,
    profile_id: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cumulative or per-profile dashboard data for the authenticated user."""
    # Fetch all user profiles
    prof_result = await db.execute(
        select(FinancialProfile)
        .where(FinancialProfile.user_id == user.id)
        .order_by(FinancialProfile.tax_year.desc())
    )
    all_profiles = prof_result.scalars().all()

    if not all_profiles:
        return {
            "mode": "cumulative",
            "profiles": [],
            "selected_profile_id": None,
            "income": 0,
            "tax_liability": 0,
            "total_savings": 0,
            "marginal_rate": None,
            "confidence": 0,
            "province": None,
            "tax_year": None,
            "insights_by_category": {},
            "chart_data": [],
        }

    # Build dropdown list — join with Document for doc_type
    doc_result = await db.execute(
        select(Document).where(Document.user_id == user.id)
    )
    docs_by_profile = {}
    for doc in doc_result.scalars().all():
        if doc.profile_id:
            docs_by_profile[doc.profile_id] = doc.doc_type

    dropdown = []
    for p in all_profiles:
        doc_type = docs_by_profile.get(p.id, "")
        label = f"{p.tax_year}"
        if doc_type:
            label += f" — {doc_type}"
        dropdown.append({
            "id": p.id,
            "tax_year": p.tax_year,
            "doc_type": doc_type or None,
            "label": label,
        })

    # Determine which profiles to aggregate
    if profile_id:
        target_profiles = [p for p in all_profiles if p.id == profile_id]
        if not target_profiles:
            target_profiles = all_profiles
            profile_id = None
    else:
        target_profiles = all_profiles

    target_ids = [p.id for p in target_profiles]
    mode = "individual" if profile_id else "cumulative"

    # Fetch only advisor-approved insights for target profiles
    from database.queries import approved_insights_query, has_pending_insights_bulk

    review_pending = await has_pending_insights_bulk(db, target_ids)
    ins_result = await db.execute(approved_insights_query(profile_ids=target_ids))
    insights = ins_result.scalars().all()

    # Aggregate income & tax liability from profile data
    total_income = 0
    total_tax_liability = 0
    marginal_rate = None
    for p in target_profiles:
        data = p.profile_data or {}
        emp = data.get("employment", {})
        derived = data.get("derived", {})
        total_income += emp.get("total_employment_income") or 0
        total_tax_liability += derived.get("estimated_tax_liability") or 0
        if mode == "individual":
            marginal_rate = derived.get("marginal_rate_combined") or 0

    # Group insights by category + build chart_data (deduplicated by name)
    from services.benefit_engine import get_insight_display_name
    by_category = {}
    chart_map: dict[str, dict] = {}  # name -> {value, category}
    cat_priority = {"ACT_NOW": 0, "THIS_YEAR": 1, "LONG_TERM": 2}
    for i in insights:
        cat = i.category or "THIS_YEAR"
        entry = {
            "id": i.insight_type,
            "headline": i.headline,
            "estimated_value": i.estimated_value or 0,
            "priority": i.priority,
        }
        by_category.setdefault(cat, []).append(entry)
        display_name = get_insight_display_name(i.insight_type)
        if display_name in chart_map:
            chart_map[display_name]["value"] += i.estimated_value or 0
            # Keep the most urgent category
            if cat_priority.get(cat, 1) < cat_priority.get(chart_map[display_name]["category"], 1):
                chart_map[display_name]["category"] = cat
        else:
            chart_map[display_name] = {"name": display_name, "value": i.estimated_value or 0, "category": cat}
    chart_data = list(chart_map.values())

    total_savings = sum(i.estimated_value or 0 for i in insights)
    confidences = [i.confidence for i in insights if i.confidence]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8

    # Province and tax_year display
    if mode == "individual":
        province = target_profiles[0].province_code
        tax_year = str(target_profiles[0].tax_year)
    else:
        years = sorted({p.tax_year for p in all_profiles})
        tax_year = f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])
        provinces = list({p.province_code for p in all_profiles if p.province_code})
        province = provinces[0] if len(provinces) == 1 else None

    return {
        "mode": mode,
        "profiles": dropdown,
        "selected_profile_id": profile_id,
        "review_pending": review_pending,
        "income": round(total_income, 2),
        "tax_liability": round(total_tax_liability, 2),
        "total_savings": round(total_savings, 2),
        "marginal_rate": round(marginal_rate, 4) if marginal_rate is not None else None,
        "confidence": round(avg_confidence, 2),
        "province": province,
        "tax_year": tax_year,
        "insights_by_category": by_category,
        "chart_data": chart_data,
    }


@router.get("/advisor")
@limiter.limit(READ_LIMIT)
async def user_advisor(
    request: Request,
    profile_id: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI Financial Advisor: health score, recommendations, deadlines."""
    # Get most recent profile or specified profile
    if profile_id:
        profile = await db.get(FinancialProfile, profile_id)
        if not profile or profile.user_id != user.id:
            profile = None
    else:
        profile = None

    if not profile:
        prof_result = await db.execute(
            select(FinancialProfile)
            .where(FinancialProfile.user_id == user.id)
            .order_by(FinancialProfile.tax_year.desc())
            .limit(1)
        )
        profile = prof_result.scalar_one_or_none()

    if not profile:
        return {
            "health_score": {"overall": 0, "components": {}},
            "last_year": {},
            "this_year": {},
            "recommendations": [],
            "calendar": [],
            "profiles": [],
        }

    # Get all profiles for dropdown
    all_prof_result = await db.execute(
        select(FinancialProfile)
        .where(FinancialProfile.user_id == user.id)
        .order_by(FinancialProfile.tax_year.desc())
    )
    all_profiles = all_prof_result.scalars().all()

    # Build dropdown
    doc_result = await db.execute(
        select(Document).where(Document.user_id == user.id)
    )
    docs_by_profile = {}
    for doc in doc_result.scalars().all():
        if doc.profile_id:
            docs_by_profile[doc.profile_id] = doc.doc_type

    dropdown = []
    for p in all_profiles:
        doc_type = docs_by_profile.get(p.id, "")
        label = f"{p.tax_year}"
        if doc_type:
            label += f" — {doc_type}"
        dropdown.append({
            "id": p.id,
            "tax_year": p.tax_year,
            "doc_type": doc_type or None,
            "label": label,
        })

    # Fetch only advisor-approved insights
    from database.queries import approved_insights_query, has_pending_insights, approved_action_items_query

    review_pending = await has_pending_insights(db, profile.id)
    ins_result = await db.execute(approved_insights_query(profile_id=profile.id))
    insights = [
        {
            "id": i.insight_type,
            "priority": i.priority,
            "category": i.category,
            "headline": i.headline,
            "detail": i.detail,
            "estimated_value": i.estimated_value,
            "action_required": i.action_required,
            "confidence": i.confidence,
        }
        for i in ins_result.scalars().all()
    ]

    # Fetch action items linked to approved insights only
    ai_result = await db.execute(
        approved_action_items_query([profile.id])
        .order_by(ActionItem.deadline.asc().nullslast())
    )
    action_items = [
        {
            "id": a.id,
            "title": a.title,
            "status": a.status,
            "priority": a.priority,
            "deadline": a.deadline.isoformat() if a.deadline else None,
            "estimated_value": a.estimated_value,
        }
        for a in ai_result.scalars().all()
    ]

    current_year = datetime.now().year
    advisor_data = build_advisor_data(
        profile_data=profile.profile_data or {},
        insights=insights,
        action_items=action_items,
        current_year=current_year,
        tax_year=profile.tax_year or 2024,
    )
    advisor_data["profiles"] = dropdown
    advisor_data["selected_profile_id"] = profile.id
    advisor_data["review_pending"] = review_pending

    return advisor_data


@router.get("/anomalies")
@limiter.limit(READ_LIMIT)
async def user_anomalies(
    request: Request,
    profile_id: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalies and potential issues across user's tax profiles."""
    from services.anomaly_detector import detect_anomalies

    if profile_id:
        profiles = [await db.get(FinancialProfile, profile_id)]
        profiles = [p for p in profiles if p and p.user_id == user.id]
    else:
        result = await db.execute(
            select(FinancialProfile)
            .where(FinancialProfile.user_id == user.id)
            .order_by(FinancialProfile.tax_year.desc())
        )
        profiles = result.scalars().all()

    all_anomalies = []
    for p in profiles:
        if not p or not p.profile_data:
            continue
        anomalies = detect_anomalies(p.profile_data)
        for a in anomalies:
            a["profile_id"] = p.id
            a["tax_year"] = p.tax_year
        all_anomalies.extend(anomalies)

    # Sort by severity across all profiles
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_anomalies.sort(key=lambda x: severity_order.get(x["severity"], 2))

    return {"anomalies": all_anomalies}
