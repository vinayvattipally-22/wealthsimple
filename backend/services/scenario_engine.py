"""What-If Scenario Simulator — deterministic tax impact calculations."""
from services.tax_engine import (
    estimated_liability,
    combined_marginal_rate,
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
    derived = profile_data.get("derived", {})
    registered = profile_data.get("registered_accounts", {})
    province = profile_data.get("province_code") or employment.get("province_of_employment", "ON")
    tax_year = profile_data.get("tax_year", 2024)
    income = employment.get("total_employment_income") or 0

    current_tax = derived.get("estimated_tax_liability") or estimated_liability(income, province, tax_year)
    current_rates = combined_marginal_rate(income, province, tax_year)
    current_marginal = current_rates[2]

    current = {
        "income": round(income, 2),
        "tax_liability": round(current_tax, 2),
        "marginal_rate": round(current_marginal, 4),
        "province": province,
    }

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
    new_tax = estimated_liability(new_income, province, tax_year)
    new_rates = combined_marginal_rate(new_income, province, tax_year)
    tax_savings = current["tax_liability"] - new_tax

    projected = {
        "income": round(new_income, 2),
        "tax_liability": round(new_tax, 2),
        "marginal_rate": round(new_rates[2], 4),
        "province": province,
    }

    return {
        "scenario_type": f"{label.lower()}_contribution",
        "current": current,
        "projected": projected,
        "impact": {
            "tax_savings": round(tax_savings, 2),
            "refund_estimate": round(tax_savings, 2),
            "effective_rate_change": round(
                (new_tax / new_income if new_income > 0 else 0)
                - (current["tax_liability"] / income if income > 0 else 0),
                4,
            ),
        },
        "explanation": (
            f"Contributing ${capped:,.0f} to your {label} reduces your taxable income "
            f"from ${income:,.0f} to ${new_income:,.0f}, saving you ${tax_savings:,.2f} in taxes. "
            f"This is an immediate refund you'll receive when you file."
        ),
    }


def _tfsa_scenario(current, amount, registered):
    """TFSA contribution — no tax impact, show growth projection."""
    amount = float(amount)
    room = registered.get("tfsa_room_remaining") or 0
    capped = min(amount, room) if room > 0 else amount

    growth_5 = capped * ((1 + TFSA_GROWTH_RATE) ** 5 - 1)
    growth_10 = capped * ((1 + TFSA_GROWTH_RATE) ** 10 - 1)
    growth_20 = capped * ((1 + TFSA_GROWTH_RATE) ** 20 - 1)

    return {
        "scenario_type": "tfsa_contribution",
        "current": current,
        "projected": current,  # No tax change
        "impact": {
            "tax_savings": 0,
            "tax_free_growth_5yr": round(growth_5, 2),
            "tax_free_growth_10yr": round(growth_10, 2),
            "tax_free_growth_20yr": round(growth_20, 2),
        },
        "explanation": (
            f"Contributing ${capped:,.0f} to your TFSA doesn't reduce your current taxes, "
            f"but all growth is tax-free. At 6% annual return, you'd earn "
            f"${growth_5:,.0f} in 5 years, ${growth_10:,.0f} in 10 years, "
            f"and ${growth_20:,.0f} in 20 years — all completely tax-free."
        ),
    }


def _income_scenario(current, old_income, province, tax_year, new_income):
    """Income change — recalculate everything."""
    new_income = float(new_income)
    new_tax = estimated_liability(new_income, province, tax_year)
    new_rates = combined_marginal_rate(new_income, province, tax_year)
    tax_delta = new_tax - current["tax_liability"]

    projected = {
        "income": round(new_income, 2),
        "tax_liability": round(new_tax, 2),
        "marginal_rate": round(new_rates[2], 4),
        "province": province,
    }

    direction = "increase" if new_income > old_income else "decrease"
    return {
        "scenario_type": "income_change",
        "current": current,
        "projected": projected,
        "impact": {
            "tax_savings": round(-tax_delta, 2),
            "tax_change": round(tax_delta, 2),
            "effective_rate_change": round(
                (new_tax / new_income if new_income > 0 else 0)
                - (current["tax_liability"] / old_income if old_income > 0 else 0),
                4,
            ),
        },
        "explanation": (
            f"If your income {'increases' if direction == 'increase' else 'decreases'} "
            f"from ${old_income:,.0f} to ${new_income:,.0f}, your tax liability "
            f"{'increases' if tax_delta > 0 else 'decreases'} by ${abs(tax_delta):,.2f}. "
            f"Your marginal rate moves from {current['marginal_rate']:.1%} to {new_rates[2]:.1%}."
        ),
    }


def _province_scenario(current, income, old_province, tax_year, new_province):
    """Province change — compare tax between provinces."""
    new_province = str(new_province).upper()[:2]
    new_tax = estimated_liability(income, new_province, tax_year)
    new_rates = combined_marginal_rate(income, new_province, tax_year)
    tax_delta = new_tax - current["tax_liability"]

    projected = {
        "income": current["income"],
        "tax_liability": round(new_tax, 2),
        "marginal_rate": round(new_rates[2], 4),
        "province": new_province,
    }

    return {
        "scenario_type": "province_change",
        "current": current,
        "projected": projected,
        "impact": {
            "tax_savings": round(-tax_delta, 2),
            "tax_change": round(tax_delta, 2),
            "effective_rate_change": round(
                (new_tax / income if income > 0 else 0)
                - (current["tax_liability"] / income if income > 0 else 0),
                4,
            ),
        },
        "explanation": (
            f"Moving from {old_province} to {new_province} would "
            f"{'save' if tax_delta < 0 else 'cost'} you ${abs(tax_delta):,.2f} in taxes. "
            f"Your marginal rate moves from {current['marginal_rate']:.1%} to {new_rates[2]:.1%}."
        ),
    }
