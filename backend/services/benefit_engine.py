"""
Benefit engine: combine LLM output with deterministic tax engine; prioritize, categorize,
format insights (20 types), value estimation, action_required, product_link, summary.
"""
from typing import Any


# Insight types from Section 9 catalog + multi-year + fallback + provincial types
INSIGHT_TYPES = [
    "RRSP_BRACKET_OPTIMIZATION", "RRSP_REFUND_ESTIMATE", "OVER_WITHHOLDING", "CPP_OVERPAYMENT", "EI_OVERPAYMENT",
    "TFSA_GAP", "FHSA_ELIGIBILITY", "CCB_STACKING", "OAS_CLAWBACK_PREVENTION", "UNION_DUES_GST_REBATE",
    "SPOUSAL_RRSP", "RRSP_GROSS_UP", "HBP_STRATEGY", "CAPITAL_LOSS_HARVEST", "DIVIDEND_OPTIMIZATION",
    "PENSION_ADJUSTMENT_IMPACT", "RETIRING_ALLOWANCE_TRANSFER", "BRACKET_STRADDLING", "RRSP_CARRY_FORWARD", "CPP_DEFERRAL",
    "INCOME_GROWTH_IMPACT", "INCOME_DECLINE_OPPORTUNITY", "YOY_TAX_EFFICIENCY",
    "SAVINGS_STARTER", "RRSP_ROOM_BUILDER", "EMERGENCY_FUND", "GST_HST_CREDIT",
    "PROVINCIAL_OTB", "PROVINCIAL_LIFT", "PROVINCIAL_HEALTH_PREMIUM",
    "PROVINCIAL_BC_CLIMATE", "PROVINCIAL_AB_ADVANTAGE", "PROVINCIAL_QC_SOLIDARITY", "PROVINCIAL_CWB",
]

CATEGORY_ACT_NOW = "ACT_NOW"
CATEGORY_THIS_YEAR = "THIS_YEAR"
CATEGORY_LONG_TERM = "LONG_TERM"



def generate_insights(profile: dict, llm_results: dict, current_year: int = None) -> dict:
    """
    Combine LLM output with deterministic calculations. Assign priority/category,
    ensure calculation_shown, action_required, product_link; build summary.
    """
    raw_insights = llm_results.get("insights", llm_results.get("insight_list", []))
    if not isinstance(raw_insights, list):
        raw_insights = []

    derived = profile.get("derived") or {}
    employment = profile.get("employment") or {}
    registered = profile.get("registered_accounts") or {}
    tax_year = profile.get("tax_year") or employment.get("tax_year") or 2024
    if not current_year:
        current_year = tax_year + 1

    # Collect RAG context for enriching insights
    rag_answers = []
    for ctx in (profile.get("rag_context") or []):
        if isinstance(ctx, dict) and ctx.get("answer"):
            rag_answers.append(ctx["answer"])

    # Enrich each insight
    insights = []
    for item in raw_insights:
        if not isinstance(item, dict):
            continue
        ins_id = item.get("id", "")
        priority = item.get("priority") or _assign_priority(item, derived)
        category = item.get("category") or _assign_category(ins_id, item)
        product_link = None
        # Enrich detail with RAG-sourced CRA guidance
        detail = item.get("detail", "")
        rag_supplement = _find_relevant_rag(ins_id, rag_answers)
        if rag_supplement:
            detail = f"{detail}\n\nCRA Guidance: {rag_supplement}" if detail else rag_supplement

        insights.append({
            "id": ins_id,
            "priority": priority,
            "category": category,
            "headline": item.get("headline", ""),
            "detail": detail,
            "estimated_value": item.get("estimated_value"),
            "calculation_shown": item.get("calculation_shown", ""),
            "action_required": item.get("action_required", ""),
            "product_link": product_link,
            "confidence": item.get("confidence", 0.8),
            "requires_additional_info": item.get("requires_additional_info") or [],
        })

    # Ensure minimum 3 insights — add fallback/provincial insights if needed
    province = (profile.get("province_code") or employment.get("province_of_employment") or "ON").upper()
    income = employment.get("total_employment_income") or 0
    rrsp_room = registered.get("rrsp_room_remaining") or registered.get("rrsp_deduction_limit") or 0
    tfsa_room = registered.get("tfsa_room_remaining") or 0

    if len(insights) < 3:
        fallbacks = _generate_fallback_insights(province, income, rrsp_room, tfsa_room, tax_year, current_year)
        for fb in fallbacks:
            if len(insights) >= 5:
                break
            # Skip if we already have a similar insight
            if any(fb["id"] == i["id"] for i in insights):
                continue
            insights.append(fb)

    # Add provincial insights if none present
    provincial_ids = {i["id"] for i in insights if "PROVINCIAL" in i.get("id", "")}
    if not provincial_ids:
        prov_insights = _generate_provincial_insights(province, income, tax_year, current_year)
        for pi in prov_insights[:2]:
            if not any(pi["id"] == i["id"] for i in insights):
                insights.append(pi)

    # Sort by estimated_value desc
    insights.sort(key=lambda x: (x.get("estimated_value") or 0), reverse=True)

    act_now = sum(1 for i in insights if i.get("category") == CATEGORY_ACT_NOW)
    this_year = sum(1 for i in insights if i.get("category") == CATEGORY_THIS_YEAR)
    long_term = sum(1 for i in insights if i.get("category") == CATEGORY_LONG_TERM)
    total_savings = sum(i.get("estimated_value") or 0 for i in insights)
    confidences = [i.get("confidence") for i in insights if i.get("confidence") is not None]
    confidence_overall = sum(confidences) / len(confidences) if confidences else 0.8

    return {
        "insights": insights,
        "summary": {
            "total_identified_savings": round(total_savings, 2),
            "act_now_count": act_now,
            "this_year_count": this_year,
            "long_term_count": long_term,
            "requires_human_review": confidence_overall < 0.85 or any(
                f in str(profile.get("flags", [])) for f in ("TAX_RATE_ANOMALY", "INCOME_DISCREPANCY")
            ),
            "confidence_overall": round(confidence_overall, 2),
        },
    }


def _find_relevant_rag(insight_id: str, rag_answers: list[str]) -> str:
    """Find the most relevant RAG answer for a given insight type."""
    if not rag_answers:
        return ""
    # Primary keyword is the first meaningful word in the ID (e.g., "RRSP" from "RRSP_BRACKET_OPTIMIZATION")
    keywords = insight_id.lower().replace("_", " ").split()
    primary = next((kw for kw in keywords if len(kw) > 2), "")

    best = ""
    best_score = 0
    for answer in rag_answers:
        lower = answer.lower()
        score = 0
        for i, kw in enumerate(keywords):
            if len(kw) <= 2:
                continue
            if kw in lower:
                score += 3 if i == 0 else 1
        # Bonus: if the primary keyword appears in the first 200 chars,
        # the answer is primarily ABOUT this topic
        if primary and primary in lower[:200]:
            score += 5
        if score > best_score:
            best_score = score
            best = answer
    if best_score >= 1 and len(best) > 20:
        # Truncate to first 500 chars to keep insights concise
        return best[:500].rsplit(".", 1)[0] + "." if len(best) > 500 else best
    return ""


def _assign_priority(item: dict, derived: dict) -> str:
    val = item.get("estimated_value") or 0
    if val >= 5000:
        return "HIGH"
    if val >= 500:
        return "MEDIUM"
    return "LOW"


def _assign_category(insight_id: str, item: dict) -> str:
    time_sensitive = ("OVER_WITHHOLDING", "CPP_OVERPAYMENT", "EI_OVERPAYMENT", "RRSP_REFUND_ESTIMATE", "BRACKET_STRADDLING")
    if insight_id in time_sensitive:
        return CATEGORY_ACT_NOW
    long_term = ("RETIREMENT", "CPP_DEFERRAL", "RRIF", "SPOUSAL_RRSP", "RRSP_CARRY_FORWARD", "TFSA_GAP",
                 "EMERGENCY_FUND", "SAVINGS_STARTER")
    if any(x in insight_id for x in long_term):
        return CATEGORY_LONG_TERM
    return CATEGORY_THIS_YEAR


def _generate_fallback_insights(province: str, income: float, rrsp_room: float, tfsa_room: float, tax_year: int = 2024, current_year: int = 2025) -> list[dict]:
    """Generate forward-looking fallback insights when LLM produces fewer than 3."""
    fallbacks = []
    monthly_income = income / 12 if income > 0 else 0
    emergency_low = round(monthly_income * 3, 0)
    emergency_high = round(monthly_income * 6, 0)

    # TFSA starter if room not used
    if tfsa_room <= 0:
        fallbacks.append({
            "id": "SAVINGS_STARTER",
            "priority": "MEDIUM",
            "category": CATEGORY_THIS_YEAR,
            "headline": f"Start building tax-free wealth in {current_year} — contribute to your TFSA before Dec 31",
            "detail": (
                f"Based on your {tax_year} data, your TFSA may be fully utilized or room hasn't been assessed yet. "
                f"In {current_year}, new TFSA room is added automatically. Even small regular contributions compound "
                "significantly over time — investments grow completely tax-free."
            ),
            "estimated_value": 0,
            "calculation_shown": "TFSA growth is tax-free; no immediate tax deduction but long-term gains are untaxed.",
            "action_required": f"Log into CRA My Account to check your {current_year} TFSA room, then set up automatic contributions.",
            "product_link": None,
            "confidence": 0.9,
            "requires_additional_info": [],
        })
    else:
        fallbacks.append({
            "id": "TFSA_GAP",
            "priority": "MEDIUM",
            "category": CATEGORY_THIS_YEAR,
            "headline": f"Lock in ${tfsa_room:,.0f} of tax-free growth before December 31, {current_year}",
            "detail": (
                f"Based on your {tax_year} records, you have ${tfsa_room:,.0f} of unused TFSA room. "
                f"Contribute this amount in {current_year} to grow your investments completely tax-free. "
                "At a 6% return, that's an extra ${0:,.0f}/year in untaxed gains.".format(round(tfsa_room * 0.06))
            ),
            "estimated_value": round(tfsa_room * 0.06, 2),
            "calculation_shown": f"Potential annual tax-free growth: ${tfsa_room:,.0f} × 6% = ${tfsa_room * 0.06:,.2f}",
            "action_required": f"Contribute ${tfsa_room:,.0f} to your TFSA before December 31, {current_year}.",
            "product_link": None,
            "confidence": 0.85,
            "requires_additional_info": [],
        })

    # RRSP room explanation
    if rrsp_room <= 0:
        rrsp_new_room = round(income * 0.18, 0)
        fallbacks.append({
            "id": "RRSP_ROOM_BUILDER",
            "priority": "LOW",
            "category": CATEGORY_LONG_TERM,
            "headline": f"Build RRSP room for {current_year + 1}: file your {tax_year} return by April 30",
            "detail": (
                f"Your {tax_year} RRSP room is $0, possibly due to a pension adjustment or full utilization. "
                f"Your {tax_year} income of ${income:,.0f} generates 18% = ${rrsp_new_room:,.0f} in new room "
                f"(minus pension adjustments). File by April 30, {current_year} to unlock this room for {current_year + 1}."
            ),
            "estimated_value": 0,
            "calculation_shown": f"RRSP room = 18% × ${income:,.0f} = ${rrsp_new_room:,.0f} − pension adjustment (PA)",
            "action_required": f"File your {tax_year} taxes by April 30, {current_year} to build RRSP room for next year.",
            "product_link": None,
            "confidence": 0.9,
            "requires_additional_info": ["pension_adjustment"],
        })

    # Emergency fund — always relevant
    fallbacks.append({
        "id": "EMERGENCY_FUND",
        "priority": "LOW",
        "category": CATEGORY_LONG_TERM,
        "headline": f"Build a ${emergency_low:,.0f}–${emergency_high:,.0f} emergency fund in {current_year} using your TFSA",
        "detail": (
            f"Based on your ${income:,.0f} income, aim for ${emergency_low:,.0f}–${emergency_high:,.0f} "
            "(3–6 months of expenses) in a high-interest savings account or TFSA. "
            "TFSA withdrawals are tax-free and the room is restored the following year — "
            f"making it ideal for emergency savings in {current_year}."
        ),
        "estimated_value": 0,
        "calculation_shown": f"Target: 3–6 months × ${monthly_income:,.0f}/mo = ${emergency_low:,.0f}–${emergency_high:,.0f}",
        "action_required": f"Set up automatic monthly transfers to a high-interest TFSA savings account in {current_year}.",
        "product_link": None,
        "confidence": 0.95,
        "requires_additional_info": [],
    })

    # GST/HST credit eligibility
    if income < 65000:
        credit_amount = 496 if income < 40000 else 248
        fallbacks.append({
            "id": "GST_HST_CREDIT",
            "priority": "MEDIUM",
            "category": CATEGORY_ACT_NOW,
            "headline": f"File by April 30 to receive ${credit_amount}/year in GST/HST credits",
            "detail": (
                f"Based on your {tax_year} income of ${income:,.0f}, you qualify for approximately "
                f"${credit_amount}/year in GST/HST credit payments. File your {tax_year} return by "
                f"April 30, {current_year} to start receiving quarterly payments in July {current_year}."
            ),
            "estimated_value": credit_amount,
            "calculation_shown": f"GST/HST credit at ${income:,.0f} income ≈ ${credit_amount}/year (quarterly payments)",
            "action_required": f"File your {tax_year} tax return by April 30, {current_year} to receive the July payment.",
            "product_link": None,
            "confidence": 0.85,
            "requires_additional_info": ["marital_status", "number_of_children"],
        })

    return fallbacks


def _generate_provincial_insights(province: str, income: float, tax_year: int = 2024, current_year: int = 2025) -> list[dict]:
    """Generate forward-looking province-specific insights."""
    insights = []

    if province == "ON":
        # Ontario Trillium Benefit
        if income < 50000:
            insights.append({
                "id": "PROVINCIAL_OTB",
                "priority": "MEDIUM",
                "category": CATEGORY_ACT_NOW,
                "headline": f"Claim up to $1,400/year in Ontario Trillium Benefit — file by April 30, {current_year}",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for the Ontario Trillium Benefit (OTB). "
                    f"File your {tax_year} return with the ON-BEN form by April 30, {current_year} "
                    f"to receive monthly OTB payments starting July {current_year}."
                ),
                "estimated_value": 1040,
                "calculation_shown": "OTB = OEPTC (up to $1,095) + OSTC (up to $345) based on income and rent/property tax",
                "action_required": f"File your {tax_year} return by April 30, {current_year} with the ON-BEN form. Report your rent or property tax.",
                "product_link": None,
                "confidence": 0.75,
                "requires_additional_info": ["rent_paid", "property_tax_paid"],
            })
        # LIFT Credit
        if income < 50000 and income > 0:
            lift_value = min(875, max(0, 875 - max(0, income - 32000) * 0.05))
            insights.append({
                "id": "PROVINCIAL_LIFT",
                "priority": "MEDIUM",
                "category": CATEGORY_THIS_YEAR,
                "headline": f"Claim up to ${lift_value:,.0f} Ontario LIFT Credit on your {tax_year} return",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for up to ${lift_value:,.0f} "
                    f"in Ontario LIFT Credit. This is automatically calculated when you file — "
                    f"file by April 30, {current_year} to claim it."
                ),
                "estimated_value": lift_value,
                "calculation_shown": f"LIFT = min($875, max(0, $875 - (${income:,.0f} - $32,000) × 5%))",
                "action_required": f"File your {tax_year} Ontario tax return by April 30, {current_year} to receive this credit.",
                "product_link": None,
                "confidence": 0.8,
                "requires_additional_info": [],
            })
        # Ontario Health Premium
        if income > 20000:
            premium = 0
            if income <= 25000:
                premium = min(300, (income - 20000) * 0.06)
            elif income <= 36000:
                premium = 300
            elif income <= 48000:
                premium = 300 + (income - 36000) * 0.06
            elif income <= 72000:
                premium = 600 + (income - 48000) * 0.25
            elif income <= 200000:
                premium = 750 + (income - 72000) * 0.25
            else:
                premium = 900
            if premium > 0:
                insights.append({
                    "id": "PROVINCIAL_HEALTH_PREMIUM",
                    "priority": "LOW",
                    "category": CATEGORY_THIS_YEAR,
                    "headline": f"Reduce your ${premium:,.0f} Ontario Health Premium in {current_year} with RRSP contributions",
                    "detail": (
                        f"If you earn similar income in {current_year}, you'll owe ${premium:,.0f} in Ontario Health Premium. "
                        f"Contributing to your RRSP before December 31, {current_year} can lower your taxable income "
                        "below the next premium threshold and reduce this amount."
                    ),
                    "estimated_value": 0,
                    "calculation_shown": f"OH Premium at ${income:,.0f} = ${premium:,.0f}",
                    "action_required": f"Contribute to RRSP before Dec 31, {current_year} to lower taxable income below the next premium tier.",
                    "product_link": None,
                    "confidence": 0.9,
                    "requires_additional_info": [],
                })

    elif province == "BC":
        credit_amount = 504 if income < 40000 else 252
        insights.append({
            "id": "PROVINCIAL_BC_CLIMATE",
            "priority": "MEDIUM",
            "category": CATEGORY_ACT_NOW,
            "headline": f"File by April 30 to receive ${credit_amount}/year in BC Climate Action Credit",
            "detail": (
                f"Based on your {tax_year} income of ${income:,.0f}, you qualify for approximately "
                f"${credit_amount}/year in BC Climate Action Tax Credit. File your {tax_year} return by "
                f"April 30, {current_year} to start receiving quarterly payments."
            ),
            "estimated_value": credit_amount,
            "calculation_shown": f"BC CATC at ${income:,.0f} ≈ ${credit_amount}/year",
            "action_required": f"File your {tax_year} BC tax return by April 30, {current_year} to receive this credit.",
            "product_link": None,
            "confidence": 0.8,
            "requires_additional_info": ["marital_status"],
        })

    elif province == "AB":
        insights.append({
            "id": "PROVINCIAL_AB_ADVANTAGE",
            "priority": "LOW",
            "category": CATEGORY_THIS_YEAR,
            "headline": f"Maximize your Alberta tax advantage in {current_year} — invest the savings",
            "detail": (
                f"Alberta's flat 10% provincial rate and no sales tax gives you more after-tax income than most provinces. "
                f"In {current_year}, direct these savings into RRSP and TFSA contributions to compound "
                "the Alberta advantage over time."
            ),
            "estimated_value": 0,
            "calculation_shown": "AB provincial rate: 10% flat vs other provinces' progressive rates",
            "action_required": f"Max out your RRSP and TFSA contributions in {current_year} to take full advantage of Alberta's lower taxes.",
            "product_link": None,
            "confidence": 0.9,
            "requires_additional_info": [],
        })

    elif province == "QC":
        credit_amount = 800 if income < 40000 else 400
        insights.append({
            "id": "PROVINCIAL_QC_SOLIDARITY",
            "priority": "MEDIUM",
            "category": CATEGORY_ACT_NOW,
            "headline": f"File by April 30 to receive ${credit_amount}/year in Quebec Solidarity Credit",
            "detail": (
                f"Based on your {tax_year} income of ${income:,.0f}, you may receive approximately "
                f"${credit_amount}/year in Quebec Solidarity Credit. File your TP-1 return by "
                f"April 30, {current_year} and complete Schedule D to start receiving payments."
            ),
            "estimated_value": credit_amount,
            "calculation_shown": f"QC Solidarity Credit at ${income:,.0f} ≈ ${credit_amount}/year",
            "action_required": f"File your {tax_year} Revenu Québec return (TP-1) by April 30, {current_year} with Schedule D.",
            "product_link": None,
            "confidence": 0.75,
            "requires_additional_info": ["rent_paid"],
        })

    # Canada Workers Benefit — all provinces, low income
    if income > 3000 and income < 33000:
        cwb = min(1518, max(0, (income - 3000) * 0.27))
        if income > 23495:
            cwb = max(0, cwb - (income - 23495) * 0.15)
        if cwb > 0:
            insights.append({
                "id": "PROVINCIAL_CWB",
                "priority": "MEDIUM",
                "category": CATEGORY_ACT_NOW,
                "headline": f"Claim ${cwb:,.0f} Canada Workers Benefit — file by April 30, {current_year}",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for ${cwb:,.0f} in "
                    f"Canada Workers Benefit. File your {tax_year} return by April 30, {current_year} to receive it. "
                    "You can also apply for advance CWB payments through CRA My Account."
                ),
                "estimated_value": round(cwb, 2),
                "calculation_shown": f"CWB = 27% × (${income:,.0f} - $3,000) phased out at higher income",
                "action_required": f"File your {tax_year} return by April 30, {current_year}. Apply for advance CWB via CRA My Account.",
                "product_link": None,
                "confidence": 0.8,
                "requires_additional_info": ["marital_status"],
            })

    return insights
