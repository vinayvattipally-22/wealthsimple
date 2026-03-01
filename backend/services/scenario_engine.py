"""What-If Scenario Simulator — deterministic tax impact calculations."""
from services.tax_engine import (
    estimated_liability,
    combined_marginal_rate,
    federal_tax,
    provincial_tax,
)


SCENARIO_TYPES = [
    "rrsp_contribution",
    "tfsa_contribution",
    "income_change",
    "province_change",
    "fhsa_contribution",
]

# Annual limits
FHSA_ANNUAL_MAX = 8000
TFSA_GROWTH_RATE = 0.06  # 6% assumed annual return
RRSP_ANNUAL_MAX = {2024: 31560, 2025: 32490}

# Province full names for explanations
PROVINCE_NAMES = {
    "ON": "Ontario", "BC": "British Columbia", "AB": "Alberta", "QC": "Quebec",
    "MB": "Manitoba", "SK": "Saskatchewan", "NS": "Nova Scotia", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "PE": "Prince Edward Island",
    "NT": "Northwest Territories", "NU": "Nunavut", "YT": "Yukon",
}


def _build_snapshot(income: float, province: str, tax_year: int) -> dict:
    """Build a complete tax snapshot for a given income/province."""
    fed = federal_tax(income, tax_year)
    prov = provincial_tax(income, province, tax_year)
    total_tax = round(fed + prov, 2)
    rates = combined_marginal_rate(income, province, tax_year)
    effective_rate = round(total_tax / income, 4) if income > 0 else 0
    take_home = round(income - total_tax, 2)
    return {
        "income": round(income, 2),
        "tax_liability": total_tax,
        "federal_tax": round(fed, 2),
        "provincial_tax": round(prov, 2),
        "marginal_rate": round(rates[2], 4),
        "federal_marginal": round(rates[0], 4),
        "provincial_marginal": round(rates[1], 4),
        "effective_rate": effective_rate,
        "take_home": take_home,
        "province": province,
    }


def _gst_hst_credit(net_income: float, tax_year: int = 2024) -> float:
    """GST/HST credit for a single individual (annual amount)."""
    base = {2024: 496, 2025: 519}.get(tax_year, 496)
    threshold = {2024: 42335, 2025: 44000}.get(tax_year, 42335)
    if net_income <= threshold:
        return float(base)
    reduction = 0.05 * (net_income - threshold)
    return round(max(0, base - reduction), 2)


def _cwb_amount(working_income: float, net_income: float, tax_year: int = 2024) -> float:
    """Canada Workers Benefit for a single individual."""
    if working_income <= 3000:
        return 0.0
    max_benefit = {2024: 1518, 2025: 1570}.get(tax_year, 1518)
    phase_in = 0.27 * (working_income - 3000)
    benefit = min(phase_in, max_benefit)
    phase_out_start = {2024: 23495, 2025: 24370}.get(tax_year, 23495)
    if net_income > phase_out_start:
        reduction = 0.15 * (net_income - phase_out_start)
        benefit = max(0, benefit - reduction)
    return round(benefit, 2)


def _add_benefit_fields(snapshot: dict, earned_income: float, province: str, tax_year: int):
    """Add RRSP room, FHSA savings, GST/HST credit, and CWB to a snapshot."""
    marginal = snapshot["marginal_rate"]
    rrsp_max = RRSP_ANNUAL_MAX.get(tax_year, 31560)
    snapshot["rrsp_room"] = min(round(earned_income * 0.18), rrsp_max)
    snapshot["rrsp_max_savings"] = round(snapshot["rrsp_room"] * marginal, 2)
    snapshot["fhsa_max_savings"] = round(min(FHSA_ANNUAL_MAX, max(0, earned_income)) * marginal, 2)
    snapshot["gst_hst_credit"] = _gst_hst_credit(earned_income, tax_year)
    snapshot["cwb"] = _cwb_amount(earned_income, earned_income, tax_year)


def simulate_scenario(profile_data: dict, scenario: dict) -> dict:
    """
    Run a what-if scenario against a user's profile.

    Args:
        profile_data: Full profile_data JSON from FinancialProfile
        scenario: {"type": str, "value": float|str}

    Returns:
        Current vs projected comparison with impact summary.
    """
    employment = profile_data.get("employment", {})
    registered = profile_data.get("registered_accounts", {})
    province = profile_data.get("province_code") or employment.get("province_of_employment", "ON")
    tax_year = profile_data.get("tax_year", 2024)
    income = employment.get("total_employment_income") or 0

    current = _build_snapshot(income, province, tax_year)

    scenario_type = scenario.get("type", "")
    value = scenario.get("value", 0)

    if scenario_type == "rrsp_contribution":
        return _rrsp_scenario(current, income, province, tax_year, value, registered)

    if scenario_type == "fhsa_contribution":
        capped = min(float(value), FHSA_ANNUAL_MAX)
        return _rrsp_scenario(current, income, province, tax_year, capped, registered, label="FHSA")

    if scenario_type == "tfsa_contribution":
        return _tfsa_scenario(current, value, registered)

    if scenario_type == "income_change":
        return _income_scenario(current, income, province, tax_year, value)

    if scenario_type == "province_change":
        return _province_scenario(current, income, province, tax_year, value)

    return {"error": f"Unknown scenario type: {scenario_type}"}


def _rrsp_scenario(current, income, province, tax_year, amount, registered, label="RRSP"):
    """RRSP/FHSA contribution — reduces taxable income."""
    amount = float(amount)
    if label == "RRSP":
        room = registered.get("rrsp_room_remaining") or 0
        capped = min(amount, room) if room > 0 else amount
    else:
        capped = min(amount, FHSA_ANNUAL_MAX)

    new_income = max(0, income - capped)
    projected = _build_snapshot(new_income, province, tax_year)
    tax_savings = current["tax_liability"] - projected["tax_liability"]
    fed_savings = current["federal_tax"] - projected["federal_tax"]
    prov_savings = current["provincial_tax"] - projected["provincial_tax"]
    effective_cost = capped - tax_savings

    explanation_parts = [
        f"**{label} Contribution Impact: ${capped:,.0f}**\n",
        f"Contributing ${capped:,.0f} to your {label} reduces your taxable income "
        f"from ${income:,.0f} to ${new_income:,.0f}.\n",
        f"**Tax Savings Breakdown:**",
        f"- Federal tax savings: ${fed_savings:,.2f}",
        f"- Provincial tax savings: ${prov_savings:,.2f}",
        f"- **Total tax savings: ${tax_savings:,.2f}**\n",
        f"**Effective Cost:** Your ${capped:,.0f} contribution effectively costs you "
        f"${effective_cost:,.0f} after the ${tax_savings:,.2f} tax refund.\n",
    ]

    if current["marginal_rate"] != projected["marginal_rate"]:
        explanation_parts.append(
            f"**Bracket Impact:** This contribution moves your marginal rate "
            f"from {current['marginal_rate']:.1%} to {projected['marginal_rate']:.1%}, "
            f"which means future dollars earned are taxed at a lower rate."
        )
    else:
        explanation_parts.append(
            f"Your marginal rate stays at {current['marginal_rate']:.1%}. "
            f"Each dollar contributed saves you {current['marginal_rate']:.1%} in tax."
        )

    if label == "RRSP":
        room = registered.get("rrsp_room_remaining") or 0
        if room > 0 and capped < room:
            remaining_room = room - capped
            explanation_parts.append(
                f"\n**RRSP Room:** You still have ${remaining_room:,.0f} of unused contribution room. "
                f"Maximizing could save an additional ${remaining_room * current['marginal_rate']:,.0f} in taxes."
            )
    elif label == "FHSA":
        explanation_parts.append(
            f"\n**FHSA Note:** Unlike RRSP, FHSA withdrawals for a first home purchase are completely tax-free — "
            f"you get the deduction now AND tax-free withdrawal later."
        )

    return {
        "scenario_type": f"{label.lower()}_contribution",
        "current": current,
        "projected": projected,
        "impact": {
            "tax_savings": round(tax_savings, 2),
            "federal_savings": round(fed_savings, 2),
            "provincial_savings": round(prov_savings, 2),
            "effective_cost": round(effective_cost, 2),
            "refund_estimate": round(tax_savings, 2),
            "effective_rate_change": round(projected["effective_rate"] - current["effective_rate"], 4),
        },
        "explanation": "\n".join(explanation_parts),
    }


def _tfsa_scenario(current, amount, registered):
    """TFSA contribution — no tax impact, show growth projection."""
    amount = float(amount)
    room = registered.get("tfsa_room_remaining") or 0
    capped = min(amount, room) if room > 0 else amount

    growth_5 = capped * ((1 + TFSA_GROWTH_RATE) ** 5 - 1)
    growth_10 = capped * ((1 + TFSA_GROWTH_RATE) ** 10 - 1)
    growth_20 = capped * ((1 + TFSA_GROWTH_RATE) ** 20 - 1)

    # Tax saved on growth (if this was in a taxable account)
    marginal = current.get("marginal_rate", 0.3)
    tax_saved_5 = round(growth_5 * marginal, 2)
    tax_saved_10 = round(growth_10 * marginal, 2)
    tax_saved_20 = round(growth_20 * marginal, 2)

    explanation_parts = [
        f"**TFSA Contribution: ${capped:,.0f}**\n",
        f"TFSA contributions don't reduce your current tax bill, but all investment "
        f"growth is completely tax-free — forever.\n",
        f"**Tax-Free Growth Projections (at 6% annual return):**",
        f"- 5 years: ${growth_5:,.0f} growth (saves ${tax_saved_5:,.0f} vs taxable account)",
        f"- 10 years: ${growth_10:,.0f} growth (saves ${tax_saved_10:,.0f} vs taxable account)",
        f"- 20 years: ${growth_20:,.0f} growth (saves ${tax_saved_20:,.0f} vs taxable account)\n",
        f"**Why TFSA over taxable?** At your {marginal:.1%} marginal rate, "
        f"investing ${capped:,.0f} in a taxable account would cost you ${tax_saved_20:,.0f} "
        f"in taxes on gains over 20 years. In your TFSA, that's all yours.\n",
    ]

    if room > 0 and capped < room:
        remaining = room - capped
        explanation_parts.append(
            f"**TFSA Room:** You still have ${remaining:,.0f} of unused contribution room. "
            f"Unused room carries forward indefinitely."
        )

    return {
        "scenario_type": "tfsa_contribution",
        "current": current,
        "projected": current,  # No tax change
        "impact": {
            "tax_savings": 0,
            "tax_free_growth_5yr": round(growth_5, 2),
            "tax_free_growth_10yr": round(growth_10, 2),
            "tax_free_growth_20yr": round(growth_20, 2),
            "tax_saved_vs_taxable_20yr": tax_saved_20,
        },
        "explanation": "\n".join(explanation_parts),
    }


def _income_scenario(current, old_income, province, tax_year, new_income):
    """Income change — recalculate everything with full breakdown."""
    new_income = float(new_income)
    projected = _build_snapshot(new_income, province, tax_year)

    # Add benefit/account impact fields
    _add_benefit_fields(current, old_income, province, tax_year)
    _add_benefit_fields(projected, new_income, province, tax_year)

    tax_delta = projected["tax_liability"] - current["tax_liability"]
    fed_delta = projected["federal_tax"] - current["federal_tax"]
    prov_delta = projected["provincial_tax"] - current["provincial_tax"]
    take_home_delta = projected["take_home"] - current["take_home"]
    income_delta = new_income - old_income

    direction = "increases" if new_income > old_income else "decreases"
    prov_name = PROVINCE_NAMES.get(province, province)

    def _arrow(delta):
        return "+" if delta > 0 else "-"

    explanation_parts = [
        f"**Income Change: ${old_income:,.0f} to ${new_income:,.0f}**\n",
        f"**Tax Breakdown:**",
        f"- Federal tax: ${current['federal_tax']:,.2f} to ${projected['federal_tax']:,.2f} "
        f"({_arrow(fed_delta)}${abs(fed_delta):,.2f})",
        f"- {prov_name} tax: ${current['provincial_tax']:,.2f} to ${projected['provincial_tax']:,.2f} "
        f"({_arrow(prov_delta)}${abs(prov_delta):,.2f})",
        f"- **Total tax: ${current['tax_liability']:,.2f} to ${projected['tax_liability']:,.2f} "
        f"({_arrow(tax_delta)}${abs(tax_delta):,.2f})**\n",
        f"**Take-Home Pay:**",
        f"- Current: ${current['take_home']:,.2f}/year (${current['take_home']/12:,.0f}/month)",
        f"- Projected: ${projected['take_home']:,.2f}/year (${projected['take_home']/12:,.0f}/month)",
    ]

    if income_delta > 0:
        marginal_on_increase = tax_delta / income_delta if income_delta != 0 else 0
        keep_rate = 1 - marginal_on_increase
        explanation_parts.append(
            f"\n**Key Insight:** Of the ${income_delta:,.0f} income increase, "
            f"you keep ${take_home_delta:,.0f} ({keep_rate:.0%}) after tax. "
            f"The rest (${tax_delta:,.0f}) goes to federal and provincial taxes."
        )
    elif income_delta < 0:
        explanation_parts.append(
            f"\n**Key Insight:** The ${abs(income_delta):,.0f} income decrease "
            f"reduces your tax by ${abs(tax_delta):,.0f}. Consider using RRSP contributions "
            f"to further reduce taxable income while your rate is lower."
        )

    if current["marginal_rate"] != projected["marginal_rate"]:
        explanation_parts.append(
            f"\n**Bracket Change:** Your marginal rate moves from "
            f"{current['marginal_rate']:.1%} to {projected['marginal_rate']:.1%}."
        )

    # Registered account impacts
    explanation_parts.append(f"\n**Registered Account Impacts:**")
    explanation_parts.append(
        f"- RRSP room: ${current['rrsp_room']:,.0f} to ${projected['rrsp_room']:,.0f} "
        f"(max tax savings: ${projected['rrsp_max_savings']:,.0f})"
    )
    explanation_parts.append(
        f"- FHSA contribution savings: ${current['fhsa_max_savings']:,.0f} to "
        f"${projected['fhsa_max_savings']:,.0f} (at ${FHSA_ANNUAL_MAX:,.0f} max contribution)"
    )

    # Benefit eligibility
    benefit_lines = []
    if current["gst_hst_credit"] > 0 or projected["gst_hst_credit"] > 0:
        if projected["gst_hst_credit"] > 0 and current["gst_hst_credit"] > 0:
            benefit_lines.append(
                f"- GST/HST Credit: ${current['gst_hst_credit']:,.2f} to ${projected['gst_hst_credit']:,.2f}/year"
            )
        elif projected["gst_hst_credit"] > 0:
            benefit_lines.append(
                f"- GST/HST Credit: You now qualify for ${projected['gst_hst_credit']:,.2f}/year"
            )
        else:
            benefit_lines.append(
                f"- GST/HST Credit: No longer eligible (was ${current['gst_hst_credit']:,.2f}/year)"
            )
    if current["cwb"] > 0 or projected["cwb"] > 0:
        if projected["cwb"] > 0 and current["cwb"] > 0:
            benefit_lines.append(
                f"- Canada Workers Benefit: ${current['cwb']:,.2f} to ${projected['cwb']:,.2f}/year"
            )
        elif projected["cwb"] > 0:
            benefit_lines.append(
                f"- Canada Workers Benefit: You now qualify for ${projected['cwb']:,.2f}/year"
            )
        else:
            benefit_lines.append(
                f"- Canada Workers Benefit: No longer eligible (was ${current['cwb']:,.2f}/year)"
            )
    if benefit_lines:
        explanation_parts.append(f"\n**Benefit Eligibility:**")
        explanation_parts.extend(benefit_lines)

    return {
        "scenario_type": "income_change",
        "current": current,
        "projected": projected,
        "impact": {
            "tax_savings": round(-tax_delta, 2),
            "tax_change": round(tax_delta, 2),
            "federal_change": round(fed_delta, 2),
            "provincial_change": round(prov_delta, 2),
            "effective_rate_change": round(projected["effective_rate"] - current["effective_rate"], 4),
            "rrsp_room_change": projected["rrsp_room"] - current["rrsp_room"],
            "gst_hst_credit_change": round(projected["gst_hst_credit"] - current["gst_hst_credit"], 2),
        },
        "explanation": "\n".join(explanation_parts),
    }


def _province_scenario(current, income, old_province, tax_year, new_province):
    """Province change — compare tax between provinces with full breakdown."""
    new_province = str(new_province).upper()[:2]
    projected = _build_snapshot(income, new_province, tax_year)

    tax_delta = projected["tax_liability"] - current["tax_liability"]
    fed_delta = projected["federal_tax"] - current["federal_tax"]
    prov_delta = projected["provincial_tax"] - current["provincial_tax"]
    take_home_delta = projected["take_home"] - current["take_home"]

    old_name = PROVINCE_NAMES.get(old_province, old_province)
    new_name = PROVINCE_NAMES.get(new_province, new_province)

    def _arrow(delta):
        return "+" if delta > 0 else "-"

    fed_note = "unchanged" if abs(fed_delta) < 1 else f"{_arrow(fed_delta)}${abs(fed_delta):,.2f}"
    explanation_parts = [
        f"**Province Move: {old_name} to {new_name}**\n",
        f"**Tax Comparison at ${income:,.0f} income:**",
        f"- Federal tax: ${current['federal_tax']:,.2f} to ${projected['federal_tax']:,.2f} ({fed_note})",
        f"- Provincial tax: ${current['provincial_tax']:,.2f} ({old_province}) to "
        f"${projected['provincial_tax']:,.2f} ({new_province}) "
        f"({_arrow(prov_delta)}${abs(prov_delta):,.2f})",
        f"- **Total: ${current['tax_liability']:,.2f} to ${projected['tax_liability']:,.2f} "
        f"({_arrow(tax_delta)}${abs(tax_delta):,.2f})**\n",
        f"**Annual Take-Home Impact:**",
        f"- {old_name}: ${current['take_home']:,.2f}/year (${current['take_home']/12:,.0f}/month)",
        f"- {new_name}: ${projected['take_home']:,.2f}/year (${projected['take_home']/12:,.0f}/month)",
        f"- **Difference: {_arrow(take_home_delta)}${abs(take_home_delta):,.2f}/year "
        f"(${abs(take_home_delta)/12:,.0f}/month)**\n",
        f"**Rate Comparison:**",
        f"- Marginal rate: {current['marginal_rate']:.1%} to {projected['marginal_rate']:.1%}",
        f"- Effective rate: {current['effective_rate']:.1%} to {projected['effective_rate']:.1%}",
    ]

    # Province-specific notes
    if new_province == "AB":
        explanation_parts.append(
            f"\n**Alberta Advantage:** Alberta has a flat 10% provincial rate and no provincial sales tax (PST), "
            f"giving you additional consumer savings beyond income tax."
        )
    elif new_province == "QC":
        explanation_parts.append(
            f"\n**Quebec Note:** Quebec has its own tax system with separate filing (TP-1). "
            f"Provincial rates are higher but Quebec offers generous family benefits and subsidized childcare."
        )
    elif new_province == "BC":
        explanation_parts.append(
            f"\n**BC Note:** BC has competitive tax rates with a Climate Action Tax Credit "
            f"that may offset some of the provincial tax burden."
        )

    return {
        "scenario_type": "province_change",
        "current": current,
        "projected": projected,
        "impact": {
            "tax_savings": round(-tax_delta, 2),
            "tax_change": round(tax_delta, 2),
            "federal_change": round(fed_delta, 2),
            "provincial_change": round(prov_delta, 2),
            "take_home_change": round(take_home_delta, 2),
            "effective_rate_change": round(projected["effective_rate"] - current["effective_rate"], 4),
        },
        "explanation": "\n".join(explanation_parts),
    }


# ---------------------------------------------------------------------------
# Feature 1: Smart Scenario Suggestions
# ---------------------------------------------------------------------------

def generate_smart_suggestions(profile_data: dict) -> list[dict]:
    """Analyze profile and return top scenario suggestions ranked by potential impact."""
    employment = profile_data.get("employment", {})
    registered = profile_data.get("registered_accounts", {})
    province = profile_data.get("province_code") or employment.get("province_of_employment", "ON")
    tax_year = profile_data.get("tax_year", 2024)
    income = employment.get("total_employment_income") or 0

    if income <= 0:
        return []

    current = _build_snapshot(income, province, tax_year)
    suggestions = []

    # 1. RRSP contribution savings
    rrsp_room = registered.get("rrsp_room_remaining") or 0
    if rrsp_room > 0:
        rrsp_savings = round(rrsp_room * current["marginal_rate"], 2)
        suggestions.append({
            "scenario_type": "rrsp_contribution",
            "title": "Maximize RRSP Contribution",
            "description": (
                f"Contributing your full ${rrsp_room:,.0f} RRSP room "
                f"could save ${rrsp_savings:,.0f} in taxes"
            ),
            "potential_savings": rrsp_savings,
            "suggested_value": rrsp_room,
            "priority": "HIGH" if rrsp_savings > 2000 else "MEDIUM",
        })

    # 2. FHSA contribution
    fhsa_savings = round(min(FHSA_ANNUAL_MAX, max(0, income)) * current["marginal_rate"], 2)
    if fhsa_savings > 0:
        suggestions.append({
            "scenario_type": "fhsa_contribution",
            "title": "FHSA Contribution",
            "description": (
                f"First-time home buyers: contribute ${FHSA_ANNUAL_MAX:,.0f} "
                f"to save ${fhsa_savings:,.0f} in taxes"
            ),
            "potential_savings": fhsa_savings,
            "suggested_value": FHSA_ANNUAL_MAX,
            "priority": "MEDIUM",
        })

    # 3. Best province move
    best_province = None
    best_savings = 0
    for prov in PROVINCE_NAMES:
        if prov == province:
            continue
        proj = _build_snapshot(income, prov, tax_year)
        savings = current["tax_liability"] - proj["tax_liability"]
        if savings > best_savings:
            best_savings = savings
            best_province = prov

    if best_province and best_savings > 500:
        suggestions.append({
            "scenario_type": "province_change",
            "title": f"Move to {PROVINCE_NAMES[best_province]}",
            "description": (
                f"Moving to {PROVINCE_NAMES[best_province]} could save "
                f"${best_savings:,.0f}/year in provincial taxes"
            ),
            "potential_savings": round(best_savings, 2),
            "suggested_value": best_province,
            "priority": "LOW",
        })

    # 4. TFSA tax-free growth
    tfsa_room = registered.get("tfsa_room_remaining") or 7000
    tfsa_20yr_growth = tfsa_room * ((1 + TFSA_GROWTH_RATE) ** 20 - 1)
    tfsa_tax_saved = round(tfsa_20yr_growth * current["marginal_rate"], 2)
    suggestions.append({
        "scenario_type": "tfsa_contribution",
        "title": "TFSA Tax-Free Growth",
        "description": (
            f"${tfsa_room:,.0f} in TFSA could generate "
            f"${tfsa_20yr_growth:,.0f} in tax-free growth over 20 years"
        ),
        "potential_savings": tfsa_tax_saved,
        "suggested_value": tfsa_room,
        "priority": "MEDIUM",
    })

    suggestions.sort(key=lambda x: x["potential_savings"], reverse=True)
    return suggestions[:4]


# ---------------------------------------------------------------------------
# Feature 2: Natural Language Scenario Parsing
# ---------------------------------------------------------------------------

def parse_natural_language_scenario(query: str, profile_data: dict) -> dict:
    """Use LLM to parse a natural language scenario query into structured params."""
    import json
    import os
    from services.llm_service import _client

    employment = profile_data.get("employment", {})
    income = employment.get("total_employment_income") or 0
    province = profile_data.get("province_code") or "ON"

    system_msg = (
        "You are a Canadian tax scenario parser. Given a user's natural language question "
        "about a tax scenario, extract the structured parameters.\n\n"
        "Return JSON with:\n"
        '- "scenarios": array of {"type": <string>, "value": <number_or_string>}\n'
        '- "explanation": brief description of what you parsed\n\n'
        "Valid types: rrsp_contribution, tfsa_contribution, fhsa_contribution, "
        "income_change, province_change\n"
        "Province codes: ON, BC, AB, QC, MB, SK, NS, NB, NL, PE, NT, NU, YT\n\n"
        "Examples:\n"
        '- "What if I contribute $5000 to RRSP?" -> [{"type":"rrsp_contribution","value":5000}]\n'
        '- "What if I earn $120K and move to Alberta?" -> '
        '[{"type":"income_change","value":120000},{"type":"province_change","value":"AB"}]\n'
        '- "Max out my TFSA and FHSA" -> '
        '[{"type":"tfsa_contribution","value":7000},{"type":"fhsa_contribution","value":8000}]\n'
    )

    user_msg = (
        f"User profile: Income ${income:,.0f}, Province: {province}\n\n"
        f"User question: {query}\n\n"
        "Parse this into scenario parameters. Return JSON only."
    )

    model = os.getenv("LLM_MODEL", "gpt-4o")
    client = _client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    result = json.loads(resp.choices[0].message.content or "{}")
    return result


# ---------------------------------------------------------------------------
# Feature 3: Multi-Year Tax Planning Projection
# ---------------------------------------------------------------------------

def multi_year_projection(
    profile_data: dict,
    years: int = 10,
    annual_rrsp: float = 0,
    annual_tfsa: float = 0,
    annual_fhsa: float = 0,
) -> dict:
    """Project RRSP tax savings, TFSA compound growth, and FHSA savings over multiple years."""
    employment = profile_data.get("employment", {})
    province = profile_data.get("province_code") or employment.get("province_of_employment", "ON")
    tax_year = profile_data.get("tax_year", 2024)
    income = employment.get("total_employment_income") or 0

    current = _build_snapshot(income, province, tax_year) if income > 0 else {"marginal_rate": 0.3}
    marginal = current["marginal_rate"]

    projections = []
    cum_rrsp_savings = 0.0
    cum_fhsa_savings = 0.0
    tfsa_balance = 0.0

    for yr in range(1, years + 1):
        rrsp_savings = round(annual_rrsp * marginal, 2)
        cum_rrsp_savings += rrsp_savings

        tfsa_balance = (tfsa_balance + annual_tfsa) * (1 + TFSA_GROWTH_RATE)
        tfsa_growth = round(tfsa_balance - (annual_tfsa * yr), 2)

        fhsa_this_year = annual_fhsa if yr <= 5 else 0
        cum_fhsa_savings += round(fhsa_this_year * marginal, 2)

        total = round(cum_rrsp_savings + max(0, tfsa_growth) + cum_fhsa_savings, 2)

        projections.append({
            "year": yr,
            "rrsp_savings": round(cum_rrsp_savings, 2),
            "tfsa_growth": max(0, tfsa_growth),
            "tfsa_balance": round(tfsa_balance, 2),
            "fhsa_savings": round(cum_fhsa_savings, 2),
            "total_benefit": total,
        })

    return {
        "scenario_type": "multi_year",
        "years": years,
        "annual_contributions": {"rrsp": annual_rrsp, "tfsa": annual_tfsa, "fhsa": annual_fhsa},
        "marginal_rate": marginal,
        "projections": projections,
        "summary": {
            "total_rrsp_savings": round(cum_rrsp_savings, 2),
            "total_tfsa_growth": max(0, round(tfsa_balance - (annual_tfsa * years), 2)),
            "total_tfsa_balance": round(tfsa_balance, 2),
            "total_fhsa_savings": round(cum_fhsa_savings, 2),
            "total_benefit": projections[-1]["total_benefit"] if projections else 0,
        },
    }
