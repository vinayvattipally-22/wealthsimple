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
    "PROVINCIAL_BC_CLIMATE", "PROVINCIAL_AB_ACFB", "PROVINCIAL_AB_CARBON_REBATE",
    "PROVINCIAL_QC_SOLIDARITY",
    "PROVINCIAL_MB_TAX_CREDIT", "PROVINCIAL_SK_LITC", "PROVINCIAL_NB_LITR",
    "PROVINCIAL_NS_ALTC", "PROVINCIAL_PE_STC",
    "PROVINCIAL_CARBON_REBATE", "PROVINCIAL_CWB",
]

# Human-readable display names for chart labels
INSIGHT_DISPLAY_NAMES = {
    "RRSP_BRACKET_OPTIMIZATION": "RRSP Optimization",
    "RRSP_REFUND_ESTIMATE": "RRSP Refund",
    "OVER_WITHHOLDING": "Over-Withholding",
    "CPP_OVERPAYMENT": "CPP Overpayment",
    "EI_OVERPAYMENT": "EI Overpayment",
    "TFSA_GAP": "TFSA Room",
    "TFSA_BENEFITS": "TFSA Benefits",
    "TFSA_START": "TFSA Starter",
    "FHSA_ELIGIBILITY": "FHSA Eligibility",
    "CCB_STACKING": "Child Benefit",
    "OAS_CLAWBACK_PREVENTION": "OAS Clawback",
    "UNION_DUES_GST_REBATE": "Union Dues Rebate",
    "SPOUSAL_RRSP": "Spousal RRSP",
    "RRSP_GROSS_UP": "RRSP Gross-Up",
    "HBP_STRATEGY": "Home Buyers' Plan",
    "CAPITAL_LOSS_HARVEST": "Capital Loss",
    "DIVIDEND_OPTIMIZATION": "Dividend Optimization",
    "PENSION_ADJUSTMENT_IMPACT": "Pension Adjustment",
    "RETIRING_ALLOWANCE_TRANSFER": "Retiring Allowance",
    "BRACKET_STRADDLING": "Bracket Straddling",
    "RRSP_CARRY_FORWARD": "RRSP Carry Forward",
    "RRSP_ROOM_EXPLANATION": "RRSP Room",
    "RRSP_ROOM_CREATION": "RRSP Room",
    "CPP_DEFERRAL": "CPP Deferral",
    "INCOME_GROWTH_IMPACT": "Income Growth",
    "INCOME_DECLINE_OPPORTUNITY": "Income Decline",
    "INCOME_CHANGE_IMPACT": "Income Change",
    "YOY_TAX_EFFICIENCY": "Tax Efficiency",
    "YEAR_OVER_YEAR_ANALYSIS": "Year-over-Year",
    "SAVINGS_STARTER": "Savings Starter",
    "RRSP_ROOM_BUILDER": "RRSP Room Builder",
    "EMERGENCY_FUND": "Emergency Fund",
    "GST_HST_CREDIT": "GST/HST Credit",
    "PROVINCIAL_OTB": "Ontario Trillium",
    "PROVINCIAL_LIFT": "Ontario LIFT",
    "PROVINCIAL_HEALTH_PREMIUM": "ON Health Premium",
    "ONTARIO_TAX_CREDITS": "Ontario Credits",
    "PROVINCIAL_BC_CLIMATE": "BC Climate Credit",
    "PROVINCIAL_AB_ACFB": "AB Child & Family",
    "PROVINCIAL_AB_CARBON_REBATE": "AB Carbon Rebate",
    "PROVINCIAL_AB_ADVANTAGE": "AB Tax Advantage",
    "PROVINCIAL_QC_SOLIDARITY": "QC Solidarity",
    "PROVINCIAL_MB_TAX_CREDIT": "MB Personal Credit",
    "PROVINCIAL_SK_LITC": "SK Low-Income Credit",
    "PROVINCIAL_NB_LITR": "NB Low-Income",
    "PROVINCIAL_NS_ALTC": "NS Affordable Living",
    "PROVINCIAL_PE_STC": "PEI Sales Tax Credit",
    "PROVINCIAL_CARBON_REBATE": "Carbon Rebate",
    "PROVINCIAL_CWB": "Workers Benefit",
}


def get_insight_display_name(insight_type: str) -> str:
    """Return a human-readable chart label for an insight type."""
    if insight_type in INSIGHT_DISPLAY_NAMES:
        return INSIGHT_DISPLAY_NAMES[insight_type]
    # Fallback: convert SNAKE_CASE to Title Case
    return insight_type.replace("PROVINCIAL_", "").replace("_", " ").title()

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
    personal_details = profile.get("personal_details") or {}
    provincial_ids = {i["id"] for i in insights if "PROVINCIAL" in i.get("id", "")}
    if not provincial_ids:
        prov_insights = _generate_provincial_insights(province, income, tax_year, current_year, personal_details)
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


def _adults_label(is_family: bool) -> str:
    return "2 adults × $345" if is_family else "1 adult × $345"


def _calculate_otb(income: float, personal: dict, tax_year: int = 2024) -> tuple[float, float, float]:
    """Calculate Ontario Trillium Benefit: returns (total_otb, oeptc, ostc)."""
    rent = float(personal.get("rent_paid") or 0)
    prop_tax = float(personal.get("property_tax_paid") or 0)
    marital = personal.get("marital_status") or "single"
    num_children = int(personal.get("num_children_under_18") or 0)
    spouse_income = float(personal.get("spouse_income") or 0)
    is_family = marital in ("married", "common_law")
    family_income = income + (spouse_income if is_family else 0)

    # OEPTC: Ontario Energy and Property Tax Credit
    # 20% of rent or full property tax, plus $277 energy component, max $1,194 (2024)
    occupancy_cost = max(rent * 0.2, prop_tax)
    oeptc_base = min(1194, occupancy_cost + 277) if occupancy_cost > 0 else 277
    oeptc_threshold = 30114 if is_family else 24092
    oeptc = max(0, oeptc_base - 0.02 * max(0, family_income - oeptc_threshold))

    # OSTC: Ontario Sales Tax Credit — $345 per adult + $345 per child
    adults = 2 if is_family else 1
    ostc_base = 345 * adults + 345 * num_children
    ostc_threshold = 41080 if is_family else 32864
    ostc = max(0, ostc_base - 0.04 * max(0, family_income - ostc_threshold))

    return round(oeptc + ostc, 2), round(oeptc, 2), round(ostc, 2)


def _generate_provincial_insights(province: str, income: float, tax_year: int = 2024, current_year: int = 2025, personal: dict | None = None) -> list[dict]:
    """Generate forward-looking province-specific insights."""
    insights = []
    personal = personal or {}

    if province == "ON":
        # Ontario Trillium Benefit
        if income < 50000:
            rent = float(personal.get("rent_paid") or 0)
            prop_tax = float(personal.get("property_tax_paid") or 0)
            has_housing_data = rent > 0 or prop_tax > 0

            otb_total, oeptc, ostc = _calculate_otb(income, personal, tax_year)

            if has_housing_data:
                # Precise calculation with housing data
                marital = personal.get("marital_status") or "single"
                num_children = int(personal.get("num_children_under_18") or 0)
                spouse_income = float(personal.get("spouse_income") or 0)
                is_family = marital in ("married", "common_law")
                family_income = income + (spouse_income if is_family else 0)

                calc_parts = []
                calc_parts.append(f"OEPTC: ${oeptc:,.2f} (occupancy cost = {'20% × $' + f'{rent:,.0f}' if rent > 0 else '$' + f'{prop_tax:,.0f}'} + $277 energy, "
                                  f"less 2% × max(0, ${family_income:,.0f} - ${'30,114' if is_family else '24,092'}))")
                child_note = f" + {num_children} child{'ren' if num_children > 1 else ''} × $345" if num_children > 0 else ""
                calc_parts.append(f"OSTC: ${ostc:,.2f} ({_adults_label(is_family)}{child_note}, "
                                  f"less 4% × max(0, ${family_income:,.0f} - ${'41,080' if is_family else '32,864'}))")

                insights.append({
                    "id": "PROVINCIAL_OTB",
                    "priority": "MEDIUM" if otb_total > 200 else "LOW",
                    "category": CATEGORY_ACT_NOW,
                    "headline": f"Claim ${otb_total:,.0f}/year in Ontario Trillium Benefit — file by April 30, {current_year}",
                    "detail": (
                        f"Based on your {tax_year} income of ${income:,.0f} and housing costs, "
                        f"you qualify for ${otb_total:,.2f} in Ontario Trillium Benefit (OTB). "
                        f"This includes ${oeptc:,.2f} OEPTC and ${ostc:,.2f} OSTC. "
                        f"File your {tax_year} return with the ON-BEN form by April 30, {current_year} "
                        f"to receive monthly OTB payments starting July {current_year}."
                    ),
                    "estimated_value": otb_total,
                    "calculation_shown": "\n".join(calc_parts) + f"\nTotal OTB = ${otb_total:,.2f}",
                    "action_required": f"File your {tax_year} return by April 30, {current_year} with the ON-BEN form.",
                    "product_link": None,
                    "confidence": 0.9,
                    "requires_additional_info": [],
                })
            else:
                # Estimate without housing data
                insights.append({
                    "id": "PROVINCIAL_OTB",
                    "priority": "MEDIUM",
                    "category": CATEGORY_ACT_NOW,
                    "headline": f"Claim up to $1,400/year in Ontario Trillium Benefit — file by April 30, {current_year}",
                    "detail": (
                        f"Based on your {tax_year} income of ${income:,.0f}, you may qualify for the Ontario Trillium Benefit (OTB). "
                        f"The exact amount depends on your rent or property tax paid. "
                        f"File your {tax_year} return with the ON-BEN form by April 30, {current_year} "
                        f"to receive monthly OTB payments starting July {current_year}."
                    ),
                    "estimated_value": otb_total,
                    "calculation_shown": "OTB = OEPTC (up to $1,194) + OSTC (up to $345/person). Provide rent or property tax for precise calculation.",
                    "action_required": f"File your {tax_year} return by April 30, {current_year} with the ON-BEN form. Report your rent or property tax.",
                    "product_link": None,
                    "confidence": 0.6,
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
        # Canada Carbon Rebate (Alberta) — all residents qualify
        # 2024: $386/adult, $193/child; couples get 2 adult amounts
        marital = personal.get("marital_status") or "single"
        num_children = int(personal.get("num_children_under_18") or 0)
        is_family = marital in ("married", "common_law")
        adults = 2 if is_family else 1
        ccr_adult = 386
        ccr_child = 193
        ccr_total = ccr_adult * adults + ccr_child * num_children
        ccr_calc_parts = [f"{adults} adult{'s' if adults > 1 else ''} × ${ccr_adult} = ${ccr_adult * adults}"]
        if num_children > 0:
            ccr_calc_parts.append(f"{num_children} child{'ren' if num_children > 1 else ''} × ${ccr_child} = ${ccr_child * num_children}")
        insights.append({
            "id": "PROVINCIAL_AB_CARBON_REBATE",
            "priority": "MEDIUM",
            "category": CATEGORY_ACT_NOW,
            "headline": f"Claim ${ccr_total}/year Canada Carbon Rebate — file by April 30, {current_year}",
            "detail": (
                f"As an Alberta resident, you qualify for ${ccr_total}/year in Canada Carbon Rebate "
                f"(formerly Climate Action Incentive). Alberta has the highest rebate in Canada due to "
                f"higher carbon pricing impact. File your {tax_year} return by April 30, {current_year} "
                f"to receive quarterly payments starting July {current_year}."
            ),
            "estimated_value": ccr_total,
            "calculation_shown": " + ".join(ccr_calc_parts) + f" = ${ccr_total}/year (paid quarterly)",
            "action_required": f"File your {tax_year} tax return by April 30, {current_year} to receive quarterly carbon rebate payments.",
            "product_link": None,
            "confidence": 0.9,
            "requires_additional_info": [],
        })

        # Alberta Child and Family Benefit (ACFB) — families with children under 18
        if num_children > 0:
            spouse_income = float(personal.get("spouse_income") or 0)
            family_income = income + (spouse_income if is_family else 0)
            # ACFB: up to $1,330/child (1 child), $1,995 (2), $2,660 (3), $3,325 (4+)
            # Phase-out starts at $25,935 (single) or $41,000 (family)
            acfb_per_child = [1330, 998, 665, 665]  # marginal per additional child
            acfb_base = sum(acfb_per_child[i] for i in range(min(num_children, len(acfb_per_child))))
            if num_children > len(acfb_per_child):
                acfb_base += acfb_per_child[-1] * (num_children - len(acfb_per_child))
            acfb_threshold = 41000 if is_family else 25935
            acfb = max(0, acfb_base - 0.04 * max(0, family_income - acfb_threshold))
            acfb = round(acfb, 2)
            if acfb > 0:
                insights.append({
                    "id": "PROVINCIAL_AB_ACFB",
                    "priority": "HIGH" if acfb > 1000 else "MEDIUM",
                    "category": CATEGORY_ACT_NOW,
                    "headline": f"Claim ${acfb:,.0f}/year Alberta Child & Family Benefit — file by April 30, {current_year}",
                    "detail": (
                        f"Based on your {tax_year} family income of ${family_income:,.0f} and {num_children} "
                        f"child{'ren' if num_children > 1 else ''} under 18, you qualify for ${acfb:,.2f}/year "
                        f"in Alberta Child and Family Benefit (ACFB). File your {tax_year} return by "
                        f"April 30, {current_year} to receive quarterly ACFB payments."
                    ),
                    "estimated_value": acfb,
                    "calculation_shown": (
                        f"ACFB base: ${acfb_base:,.0f} for {num_children} child{'ren' if num_children > 1 else ''}, "
                        f"less 4% × max(0, ${family_income:,.0f} - ${acfb_threshold:,}) = ${acfb:,.2f}"
                    ),
                    "action_required": f"File your {tax_year} tax return by April 30, {current_year} to receive quarterly ACFB payments.",
                    "product_link": None,
                    "confidence": 0.85,
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

    elif province == "MB":
        # Manitoba Personal Tax Credit + Education Property Tax Credit
        if income < 40000:
            mb_ptc = min(504, max(0, 504 - max(0, income - 25921) * 0.035))
            insights.append({
                "id": "PROVINCIAL_MB_TAX_CREDIT",
                "priority": "MEDIUM",
                "category": CATEGORY_THIS_YEAR,
                "headline": f"Claim up to ${mb_ptc:,.0f} Manitoba Personal Tax Credit on your {tax_year} return",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for approximately "
                    f"${mb_ptc:,.0f} in Manitoba Personal Tax Credit. Manitoba also offers the Education "
                    f"Property Tax Credit (up to $700) if you pay rent or property tax."
                ),
                "estimated_value": mb_ptc,
                "calculation_shown": f"MB PTC ≈ ${mb_ptc:,.0f} at ${income:,.0f} income. Education Property Tax Credit up to $700 additional.",
                "action_required": f"File your {tax_year} Manitoba return by April 30, {current_year}. Report rent paid on MB479.",
                "product_link": None,
                "confidence": 0.75,
                "requires_additional_info": ["rent_paid", "property_tax_paid"],
            })

    elif province == "SK":
        # Saskatchewan Low-Income Tax Credit (SLITC)
        if income < 35000 and income > 0:
            sk_litc = min(432, max(0, 432 - max(0, income - 16610) * 0.02))
            insights.append({
                "id": "PROVINCIAL_SK_LITC",
                "priority": "MEDIUM",
                "category": CATEGORY_ACT_NOW,
                "headline": f"Claim ${sk_litc:,.0f} Saskatchewan Low-Income Tax Credit — file by April 30, {current_year}",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for approximately "
                    f"${sk_litc:,.0f} in Saskatchewan Low-Income Tax Credit (SLITC). File your {tax_year} "
                    f"return by April 30, {current_year} to receive quarterly payments."
                ),
                "estimated_value": round(sk_litc, 2),
                "calculation_shown": f"SK LITC = max(0, $432 − 2% × max(0, ${income:,.0f} − $16,610)) = ${sk_litc:,.2f}",
                "action_required": f"File your {tax_year} Saskatchewan return by April 30, {current_year}.",
                "product_link": None,
                "confidence": 0.8,
                "requires_additional_info": [],
            })

    elif province == "NB":
        # New Brunswick Low-Income Tax Reduction
        if income < 22000 and income > 0:
            nb_litr = min(681, max(0, 681 - max(0, income - 16878) * 0.04))
            insights.append({
                "id": "PROVINCIAL_NB_LITR",
                "priority": "MEDIUM",
                "category": CATEGORY_THIS_YEAR,
                "headline": f"Claim ${nb_litr:,.0f} NB Low-Income Tax Reduction on your {tax_year} return",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for approximately "
                    f"${nb_litr:,.0f} in New Brunswick Low-Income Tax Reduction."
                ),
                "estimated_value": round(nb_litr, 2),
                "calculation_shown": f"NB LITR = max(0, $681 − 4% × max(0, ${income:,.0f} − $16,878)) = ${nb_litr:,.2f}",
                "action_required": f"File your {tax_year} NB return by April 30, {current_year}.",
                "product_link": None,
                "confidence": 0.8,
                "requires_additional_info": [],
            })

    elif province == "NS":
        # Nova Scotia Affordable Living Tax Credit
        if income < 36000 and income > 0:
            ns_altc = min(500, max(0, 500 - max(0, income - 15000) * 0.05))
            insights.append({
                "id": "PROVINCIAL_NS_ALTC",
                "priority": "MEDIUM",
                "category": CATEGORY_ACT_NOW,
                "headline": f"Claim ${ns_altc:,.0f} NS Affordable Living Tax Credit — file by April 30, {current_year}",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for approximately "
                    f"${ns_altc:,.0f} in Nova Scotia Affordable Living Tax Credit. File your {tax_year} "
                    f"return by April 30, {current_year} to receive quarterly payments."
                ),
                "estimated_value": round(ns_altc, 2),
                "calculation_shown": f"NS ALTC = max(0, $500 − 5% × max(0, ${income:,.0f} − $15,000)) = ${ns_altc:,.2f}",
                "action_required": f"File your {tax_year} Nova Scotia return by April 30, {current_year}.",
                "product_link": None,
                "confidence": 0.8,
                "requires_additional_info": [],
            })

    elif province == "PE":
        # PEI Sales Tax Credit
        if income < 36000 and income > 0:
            pe_stc = min(110, max(0, 110 - max(0, income - 30000) * 0.02))
            insights.append({
                "id": "PROVINCIAL_PE_STC",
                "priority": "LOW",
                "category": CATEGORY_THIS_YEAR,
                "headline": f"Claim ${pe_stc:,.0f} PEI Sales Tax Credit on your {tax_year} return",
                "detail": (
                    f"Based on your {tax_year} income of ${income:,.0f}, you qualify for approximately "
                    f"${pe_stc:,.0f} in PEI Sales Tax Credit."
                ),
                "estimated_value": round(pe_stc, 2),
                "calculation_shown": f"PEI STC = max(0, $110 − 2% × max(0, ${income:,.0f} − $30,000)) = ${pe_stc:,.2f}",
                "action_required": f"File your {tax_year} PEI return by April 30, {current_year}.",
                "product_link": None,
                "confidence": 0.8,
                "requires_additional_info": [],
            })

    # Canada Carbon Rebate (CCR) — all provinces except AB (handled above) and QC (has own system)
    if province not in ("AB", "QC"):
        marital = personal.get("marital_status") or "single"
        num_children = int(personal.get("num_children_under_18") or 0)
        is_family = marital in ("married", "common_law")
        adults = 2 if is_family else 1
        # 2024 rates by province (per adult, quarterly)
        ccr_rates = {
            "ON": 140, "MB": 150, "SK": 188, "NB": 95, "NS": 103,
            "PE": 110, "NL": 149, "BC": 0, "NT": 0, "NU": 0, "YT": 0,
        }
        ccr_adult = ccr_rates.get(province, 120)
        if ccr_adult > 0:
            ccr_child = round(ccr_adult * 0.5)
            ccr_total = ccr_adult * adults + ccr_child * num_children
            insights.append({
                "id": "PROVINCIAL_CARBON_REBATE",
                "priority": "MEDIUM" if ccr_total > 200 else "LOW",
                "category": CATEGORY_ACT_NOW,
                "headline": f"Claim ${ccr_total}/year Canada Carbon Rebate — file by April 30, {current_year}",
                "detail": (
                    f"As a {province} resident, you qualify for ${ccr_total}/year in Canada Carbon Rebate. "
                    f"File your {tax_year} return by April 30, {current_year} to receive quarterly payments."
                ),
                "estimated_value": ccr_total,
                "calculation_shown": f"{adults} adult{'s' if adults > 1 else ''} × ${ccr_adult} + {num_children} child{'ren' if num_children > 1 else ''} × ${ccr_child} = ${ccr_total}/year",
                "action_required": f"File your {tax_year} tax return by April 30, {current_year}.",
                "product_link": None,
                "confidence": 0.85,
                "requires_additional_info": [],
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
