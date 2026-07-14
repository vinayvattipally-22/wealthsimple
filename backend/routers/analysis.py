"""Analysis endpoints: trigger pipeline, status, results, dashboard, SSE streaming."""
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from sqlalchemy import select, and_, delete
from database.models import FinancialProfile, Insight, ReviewCase, ActionItem, User

from services.tax_engine import (
    estimated_liability, combined_marginal_rate,
    cpp_overpayment, ei_overpayment, over_withholding_estimate, bracket_analysis,
)
from services.llm_service import verify_extraction, analyze_financials
from services.benefit_engine import generate_insights
from services.action_planner import generate_action_items
from middleware.rate_limiter import limiter, ANALYSIS_LIMIT, READ_LIMIT
from middleware.auth import get_current_user_optional

router = APIRouter()

# Agent identity metadata for each pipeline stage
AGENT_DEFS = {
    "extraction": {
        "agent_name": "Data Extractor",
        "agent_description": "Loads and validates your financial profile data",
    },
    "tax_engine": {
        "agent_name": "Tax Calculator",
        "agent_description": "Computes your tax liability and marginal rates using CRA brackets",
    },
    "llm_analysis": {
        "agent_name": "Tax Strategist",
        "agent_description": "Analyzes your finances with GPT-4o to find optimization opportunities",
    },
    "rag_query": {
        "agent_name": "Knowledge Researcher",
        "agent_description": "Queries CRA knowledge base for relevant tax guidance",
    },
    "benefit_engine": {
        "agent_name": "Insight Generator",
        "agent_description": "Generates prioritized, actionable insights with dollar estimates",
    },
    "compliance": {
        "agent_name": "Compliance Checker",
        "agent_description": "Checks for CRA audit risk flags and deadline compliance",
    },
    "action_planner": {
        "agent_name": "Action Planner",
        "agent_description": "Converts insights into trackable action items with deadlines",
    },
}


async def _get_prior_year_data(db: AsyncSession, user_id: int | None, tax_year: int) -> dict | None:
    """Query for prior year profile belonging to same user."""
    if not user_id:
        return None
    result = await db.execute(
        select(FinancialProfile).where(
            and_(
                FinancialProfile.user_id == user_id,
                FinancialProfile.tax_year < tax_year,
            )
        ).order_by(FinancialProfile.tax_year.desc()).limit(1)
    )
    prior = result.scalar_one_or_none()
    if not prior or not prior.profile_data:
        return None
    prior_data = prior.profile_data
    prior_employment = prior_data.get("employment", {})
    prior_income = prior_employment.get("total_employment_income") or 0
    prior_tax = prior_employment.get("total_income_tax_withheld") or 0
    prior_rrsp = (prior_data.get("registered_accounts") or {}).get("rrsp_contributions") or 0
    return {
        "prior_tax_year": prior.tax_year,
        "prior_year_income": prior_income,
        "prior_year_tax": prior_tax,
        "prior_year_rrsp": prior_rrsp,
        "prior_province": prior.province_code,
    }


@router.post("/analyze/{profile_id}")
@limiter.limit(ANALYSIS_LIMIT)
async def trigger_analysis(
    request: Request,
    profile_id: int,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Trigger full analysis pipeline for profile: verify extraction, run tax engine, LLM analysis, benefit engine, queue case."""
    result = await db.get(FinancialProfile, profile_id)
    if not result:
        raise HTTPException(404, "Profile not found")
    profile = result
    data = profile.profile_data or {}
    employment = data.get("employment", {})
    registered = data.get("registered_accounts", {})
    province = data.get("province_code") or employment.get("province_of_employment") or "ON"
    tax_year = data.get("tax_year", 2024)
    income = employment.get("total_employment_income") or 0
    box_22 = employment.get("total_income_tax_withheld") or 0
    rrsp_room = (registered.get("rrsp_room_remaining") or registered.get("rrsp_deduction_limit") or 0)
    tfsa_room = registered.get("tfsa_room_remaining") or 0
    prior_net = data.get("derived", {}).get("estimated_net_income")
    capital_loss = data.get("carryforwards", {}).get("capital_loss_carryforward")
    hbp = registered.get("hbp_balance_outstanding")
    # Query prior year data for multi-year comparison
    prior_year_data = await _get_prior_year_data(db, user.id if user else profile.user_id, tax_year)
    if prior_year_data and income:
        prior_income = prior_year_data.get("prior_year_income") or 0
        if prior_income > 0:
            prior_year_data["income_change_pct"] = round(((income - prior_income) / prior_income) * 100, 1)
    # Verify extraction (optional; if we already have structured data we can skip)
    from datetime import datetime, timedelta
    current_year = datetime.now().year
    structured = data.get("structured_t4") or employment
    llm_result = analyze_financials(
        structured_fields=structured,
        rrsp_room=rrsp_room,
        tfsa_room=tfsa_room,
        province=province,
        tax_year=tax_year,
        prior_net_income=prior_net,
        capital_loss_cf=capital_loss,
        hbp_balance=hbp,
        prior_year_data=prior_year_data,
        current_year=current_year,
    )
    insights_data = llm_result.get("insights", llm_result.get("insight_list", []))
    if not isinstance(insights_data, list):
        insights_data = []
    # Deterministic derived values
    derived = data.get("derived") or {}
    derived["estimated_tax_liability"] = estimated_liability(income, province, tax_year)
    derived["marginal_rate_combined"] = combined_marginal_rate(income, province, tax_year)[2]
    # Query knowledge graph for supporting tax guidance
    from services.lightrag_service import query_tax_guidance
    rag_context = []
    try:
        questions = []
        if rrsp_room and rrsp_room > 0:
            questions.append(f"What are the RRSP contribution rules and tax benefits for {tax_year} with ${rrsp_room:.0f} contribution room?")
        if tfsa_room and tfsa_room > 0:
            questions.append(f"What are the TFSA rules and contribution limits for {tax_year}?")
        if income and income > 50000:
            questions.append(f"What tax planning strategies apply for ${income:.0f} employment income in {province} for {tax_year}?")
        if not questions:
            questions.append(f"What are the key tax considerations for {tax_year} in {province}?")
        for q in questions[:3]:
            result = await query_tax_guidance(q, mode="hybrid")
            rag_context.append(result)
    except Exception:
        pass  # RAG is supplementary; don't fail the pipeline if unavailable

    # Benefit engine: prioritize and format
    full_profile = {**data, "derived": derived, "rag_context": rag_context}
    insights_result = generate_insights(full_profile, llm_result, current_year=current_year)
    # Remove old insights and action items for this profile before inserting new ones
    await db.execute(delete(ActionItem).where(ActionItem.profile_id == profile_id))
    await db.execute(delete(Insight).where(Insight.profile_id == profile_id))

    # Generate action items from insights
    action_items_data = generate_action_items(
        insights_result.get("insights", []),
        data,
        tax_year,
    )

    # Persist insights, action items, and create review case
    case = ReviewCase(
        profile_id=profile_id,
        status="PENDING",
        confidence_score=insights_result.get("summary", {}).get("confidence_overall"),
        sla_due_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(case)
    await db.flush()

    insight_db_map = {}
    for ins in insights_result.get("insights", [])[:50]:
        ob = Insight(
            profile_id=profile_id,
            insight_type=ins.get("id", ""),
            priority=ins.get("priority"),
            category=ins.get("category"),
            headline=ins.get("headline"),
            detail=ins.get("detail"),
            estimated_value=ins.get("estimated_value"),
            calculation_shown=ins.get("calculation_shown"),
            action_required=ins.get("action_required"),
            product_link=ins.get("product_link"),
            confidence=ins.get("confidence"),
            requires_additional_info=ins.get("requires_additional_info"),
            review_status="PENDING",
        )
        db.add(ob)
        await db.flush()
        insight_db_map[ins.get("id", "")] = ob.id

    # Persist action items
    from dateutil.parser import isoparse
    for ai in action_items_data:
        deadline = None
        if ai.get("deadline"):
            try:
                deadline = isoparse(ai["deadline"])
            except Exception:
                pass
        db.add(ActionItem(
            profile_id=profile_id,
            insight_id=insight_db_map.get(ai.get("insight_type")),
            title=ai["title"],
            description=ai.get("description"),
            deadline=deadline,
            priority=ai.get("priority"),
            status="pending",
            estimated_value=ai.get("estimated_value"),
        ))

    profile.review_status = "PENDING"
    profile.profile_data = {**data, "derived": derived}
    await db.commit()
    return {"profile_id": profile_id, "case_id": case.id, "insights_count": len(insights_result.get("insights", []))}


@router.get("/analysis/{profile_id}/status")
async def analysis_status(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Return analysis progress for profile."""
    profile = await db.get(FinancialProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return {
        "profile_id": profile_id,
        "review_status": profile.review_status,
        "approved_at": profile.approved_at.isoformat() if profile.approved_at else None,
    }


@router.get("/analysis/{profile_id}/results")
async def analysis_results(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Return approved insights and summary for profile."""
    from database.queries import approved_insights_query, has_pending_insights

    profile = await db.get(FinancialProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    review_pending = await has_pending_insights(db, profile_id)
    result = await db.execute(approved_insights_query(profile_id=profile_id))
    insights = result.scalars().all()
    return {
        "profile_id": profile_id,
        "review_pending": review_pending,
        "insights": [
            {
                "id": i.insight_type,
                "priority": i.priority,
                "category": i.category,
                "headline": i.headline,
                "detail": i.detail,
                "estimated_value": i.estimated_value,
                "action_required": i.action_required,
                "product_link": i.product_link,
            }
            for i in insights
        ],
        "summary": (profile.profile_data or {}).get("derived", {}),
    }


@router.get("/analysis/{profile_id}/dashboard")
@limiter.limit(READ_LIMIT)
async def dashboard_data(request: Request, profile_id: int, db: AsyncSession = Depends(get_db)):
    """Return aggregated chart-ready data for the dashboard."""
    profile = await db.get(FinancialProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    data = profile.profile_data or {}
    employment = data.get("employment", {})
    derived = data.get("derived", {})
    income = employment.get("total_employment_income") or 0
    province = profile.province_code or "ON"

    from database.queries import approved_insights_query, has_pending_insights

    review_pending = await has_pending_insights(db, profile_id)
    result = await db.execute(approved_insights_query(profile_id=profile_id))
    insights = result.scalars().all()

    # Group insights by category
    from services.benefit_engine import get_insight_display_name
    by_category = {"ACT_NOW": [], "THIS_YEAR": [], "LONG_TERM": []}
    chart_data = []
    for i in insights:
        cat = i.category or "THIS_YEAR"
        entry = {
            "id": i.insight_type,
            "headline": i.headline,
            "estimated_value": i.estimated_value or 0,
            "priority": i.priority,
        }
        by_category.setdefault(cat, []).append(entry)
        chart_data.append({"name": get_insight_display_name(i.insight_type), "value": i.estimated_value or 0, "category": cat})

    total_savings = sum(i.estimated_value or 0 for i in insights)
    confidences = [i.confidence for i in insights if i.confidence]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8

    return {
        "profile_id": profile_id,
        "review_pending": review_pending,
        "income": income,
        "province": province,
        "tax_year": profile.tax_year,
        "tax_liability": derived.get("estimated_tax_liability", 0),
        "marginal_rate": derived.get("marginal_rate_combined", 0),
        "total_savings": round(total_savings, 2),
        "confidence": round(avg_confidence, 2),
        "insights_by_category": by_category,
        "chart_data": chart_data,
    }


@router.get("/analyze/{profile_id}/stream")
async def stream_analysis(
    profile_id: int,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Stream analysis pipeline progress via Server-Sent Events."""
    profile = await db.get(FinancialProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    data = profile.profile_data or {}
    employment = data.get("employment", {})
    registered = data.get("registered_accounts", {})
    province = data.get("province_code") or employment.get("province_of_employment") or "ON"
    tax_year = data.get("tax_year", 2024)
    income = employment.get("total_employment_income") or 0
    rrsp_room = registered.get("rrsp_room_remaining") or 0
    tfsa_room = registered.get("tfsa_room_remaining") or 0

    from datetime import datetime, timedelta
    current_year = datetime.now().year

    # Query prior year data for multi-year comparison
    prior_year_data = await _get_prior_year_data(db, user.id if user else profile.user_id, tax_year)
    if prior_year_data and income:
        prior_income = prior_year_data.get("prior_year_income") or 0
        if prior_income > 0:
            prior_year_data["income_change_pct"] = round(((income - prior_income) / prior_income) * 100, 1)

    async def event_generator():
        # Stage 1: Data Extractor
        yield _sse_stage("extraction", "complete", f"Loaded {tax_year} data — planning your {current_year} strategy")
        await asyncio.sleep(0.1)

        # Stage 2: Tax Calculator
        yield _sse_stage("tax_engine", "running", f"Calculating your tax position for {current_year} planning...")
        derived = data.get("derived") or {}
        derived["estimated_tax_liability"] = estimated_liability(income, province, tax_year)
        derived["marginal_rate_combined"] = combined_marginal_rate(income, province, tax_year)[2]
        yield _sse_stage("tax_engine", "complete", f"Tax liability: ${derived['estimated_tax_liability']:,.2f}")
        await asyncio.sleep(0.1)

        # Stage 3: Tax Strategist
        yield _sse_stage("llm_analysis", "running", f"Identifying savings opportunities for {current_year}...")
        structured = data.get("structured_t4") or employment
        llm_result = analyze_financials(
            structured_fields=structured, rrsp_room=rrsp_room, tfsa_room=tfsa_room,
            province=province, tax_year=tax_year, prior_year_data=prior_year_data,
            current_year=current_year,
        )
        yield _sse_stage("llm_analysis", "complete", f"{current_year} optimization strategies identified")
        await asyncio.sleep(0.1)

        # Stage 4: Knowledge Researcher
        yield _sse_stage("rag_query", "running", f"Checking {current_year} contribution limits and deadlines...")
        rag_context = []
        try:
            from services.lightrag_service import query_tax_guidance
            questions = []
            if rrsp_room and rrsp_room > 0:
                questions.append(f"What are the RRSP contribution rules and tax benefits for {current_year} with ${rrsp_room:.0f} contribution room?")
            if tfsa_room and tfsa_room > 0:
                questions.append(f"What are the TFSA rules and contribution limits for {current_year}?")
            if income and income > 50000:
                questions.append(f"What tax planning strategies apply for ${income:.0f} employment income in {province} for {current_year}?")
            if not questions:
                questions.append(f"What are the key tax considerations for {current_year} in {province}?")
            for q in questions[:3]:
                r = await query_tax_guidance(q, mode="hybrid")
                rag_context.append(r)
        except Exception:
            pass
        yield _sse_stage("rag_query", "complete", f"{len(rag_context)} knowledge sources retrieved")
        await asyncio.sleep(0.1)

        # Stage 5: Insight Generator
        yield _sse_stage("benefit_engine", "running", f"Building your {current_year} optimization plan...")
        full_profile = {**data, "derived": derived, "rag_context": rag_context}
        insights_result = generate_insights(full_profile, llm_result, current_year=current_year)
        yield _sse_stage("benefit_engine", "complete", f"{len(insights_result.get('insights', []))} insights generated")

        # Stream individual insights
        for ins in insights_result.get("insights", []):
            yield _sse("insight", {
                "id": ins.get("id"),
                "headline": ins.get("headline"),
                "estimated_value": ins.get("estimated_value"),
                "priority": ins.get("priority"),
                "category": ins.get("category"),
            })
            await asyncio.sleep(0.05)

        # Stage 6: Compliance Checker
        yield _sse_stage("compliance", "running", "Reviewing deadlines and time-sensitive actions...")
        compliance_flags = []
        box_22 = employment.get("total_income_tax_withheld") or 0
        total_cpp = employment.get("total_cpp_contributions") or 0
        total_ei = employment.get("total_ei_premiums") or 0

        # CPP overpayment
        cpp_over = cpp_overpayment(total_cpp, tax_year)
        if cpp_over > 0:
            compliance_flags.append({"flag": "CPP_OVERPAYMENT", "message": f"CPP overpayment of ${cpp_over:,.2f} detected — refund available", "severity": "info"})

        # EI overpayment
        ei_over = ei_overpayment(total_ei, tax_year)
        if ei_over > 0:
            compliance_flags.append({"flag": "EI_OVERPAYMENT", "message": f"EI overpayment of ${ei_over:,.2f} detected — refund available", "severity": "info"})

        # Over-withholding
        est_tax = derived.get("estimated_tax_liability", 0)
        over_withheld = over_withholding_estimate(box_22, est_tax)
        if over_withheld > 500:
            compliance_flags.append({"flag": "OVER_WITHHOLDING", "message": f"Over-withheld by ${over_withheld:,.2f} — expect a refund", "severity": "info"})

        # Bracket proximity
        try:
            bracket_info = bracket_analysis(income, province, tax_year)
            if bracket_info and bracket_info.get("distance_to_next", 0) < 5000:
                compliance_flags.append({"flag": "BRACKET_PROXIMITY", "message": f"${bracket_info['distance_to_next']:,.0f} from next tax bracket — consider RRSP contribution", "severity": "warning"})
        except Exception:
            pass

        # RRSP deadline check
        now = datetime.utcnow()
        rrsp_deadline = datetime(tax_year + 1, 3, 3)
        if now < rrsp_deadline and rrsp_room > 0:
            days_left = (rrsp_deadline - now).days
            if days_left <= 30:
                compliance_flags.append({"flag": "RRSP_DEADLINE", "message": f"RRSP deadline in {days_left} days — contribute before March 3", "severity": "warning"})

        # Filing deadline check
        filing_deadline = datetime(tax_year + 1, 4, 30)
        if now < filing_deadline:
            days_to_file = (filing_deadline - now).days
            if days_to_file <= 60:
                compliance_flags.append({"flag": "FILING_DEADLINE", "message": f"Tax filing deadline in {days_to_file} days", "severity": "info"})

        for flag in compliance_flags:
            yield _sse("compliance", flag)
            await asyncio.sleep(0.05)
        yield _sse_stage("compliance", "complete", f"{len(compliance_flags)} compliance checks completed")
        await asyncio.sleep(0.1)

        # Stage 7: Action Planner
        yield _sse_stage("action_planner", "running", f"Scheduling your {current_year} financial milestones...")
        action_items_data = generate_action_items(
            insights_result.get("insights", []),
            data,
            tax_year,
        )
        yield _sse_stage("action_planner", "complete", f"{len(action_items_data)} action items created")

        # Remove old insights and action items before persisting new ones
        await db.execute(delete(ActionItem).where(ActionItem.profile_id == profile_id))
        await db.execute(delete(Insight).where(Insight.profile_id == profile_id))

        # Persist results
        case = ReviewCase(
            profile_id=profile_id, status="PENDING",
            confidence_score=insights_result.get("summary", {}).get("confidence_overall"),
            flags=[f["flag"] for f in compliance_flags] if compliance_flags else None,
            sla_due_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(case)
        await db.flush()

        # Persist insights
        insight_db_map = {}
        for ins in insights_result.get("insights", [])[:50]:
            ob = Insight(
                profile_id=profile_id, insight_type=ins.get("id", ""),
                priority=ins.get("priority"), category=ins.get("category"),
                headline=ins.get("headline"), detail=ins.get("detail"),
                estimated_value=ins.get("estimated_value"),
                calculation_shown=ins.get("calculation_shown"),
                action_required=ins.get("action_required"),
                product_link=ins.get("product_link"),
                confidence=ins.get("confidence"),
                requires_additional_info=ins.get("requires_additional_info"),
                review_status="PENDING",
            )
            db.add(ob)
            await db.flush()
            insight_db_map[ins.get("id", "")] = ob.id

        # Persist action items
        from dateutil.parser import isoparse
        for ai in action_items_data:
            deadline = None
            if ai.get("deadline"):
                try:
                    deadline = isoparse(ai["deadline"])
                except Exception:
                    pass
            db.add(ActionItem(
                profile_id=profile_id,
                insight_id=insight_db_map.get(ai.get("insight_type")),
                title=ai["title"],
                description=ai.get("description"),
                deadline=deadline,
                priority=ai.get("priority"),
                status="pending",
                estimated_value=ai.get("estimated_value"),
            ))

        profile.review_status = "PENDING"
        profile.profile_data = {**data, "derived": derived}
        await db.commit()

        total_savings = insights_result.get("summary", {}).get("total_identified_savings", 0)
        yield _sse("complete", {
            "total_insights": len(insights_result.get("insights", [])),
            "total_savings": total_savings,
            "case_id": case.id,
            "action_items_count": len(action_items_data),
            "compliance_flags": len(compliance_flags),
            "review_pending": True,
        })

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _sse_stage(stage: str, status: str, message: str) -> str:
    """Format a stage SSE event with agent metadata."""
    agent = AGENT_DEFS.get(stage, {})
    return _sse("stage", {
        "stage": stage,
        "status": status,
        "message": message,
        "agent_name": agent.get("agent_name", stage),
        "agent_description": agent.get("agent_description", ""),
    })
