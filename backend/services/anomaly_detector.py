"""Anomaly detection for tax profiles: CPP/EI overpayment, withholding issues, unused deductions."""
from services.tax_engine import cpp_overpayment, ei_overpayment, over_withholding_estimate


def detect_anomalies(profile_data: dict) -> list[dict]:
    """Scan profile data for anomalies and potential issues.

    Returns a list of anomaly dicts sorted by severity (critical > warning > info).
    """
    anomalies = []
    employment = profile_data.get("employment", {})
    registered = profile_data.get("registered_accounts", {})
    derived = profile_data.get("derived", {})
    tax_year = profile_data.get("tax_year", 2024)

    income = employment.get("total_employment_income") or 0
    tax_withheld = employment.get("total_income_tax_withheld") or 0
    cpp = employment.get("total_cpp_contributions") or 0
    ei = employment.get("total_ei_premiums") or 0
    rrsp_room = registered.get("rrsp_room_remaining") or 0
    est_tax = derived.get("estimated_tax_liability") or 0
    marginal = derived.get("marginal_rate_combined") or 0

    # 1. CPP overpayment
    cpp_over = cpp_overpayment(cpp, tax_year)
    if cpp_over > 0:
        anomalies.append({
            "type": "CPP_OVERPAYMENT",
            "severity": "info",
            "title": "CPP Overpayment Detected",
            "description": f"You overpaid CPP by ${cpp_over:,.2f}. This will be refunded when you file your return.",
            "amount": cpp_over,
        })

    # 2. EI overpayment
    ei_over = ei_overpayment(ei, tax_year)
    if ei_over > 0:
        anomalies.append({
            "type": "EI_OVERPAYMENT",
            "severity": "info",
            "title": "EI Overpayment Detected",
            "description": f"You overpaid EI premiums by ${ei_over:,.2f}. This will be refunded when you file your return.",
            "amount": ei_over,
        })

    # 3. Over-withholding (employer withheld more than estimated tax)
    if tax_withheld and est_tax and tax_withheld > est_tax * 1.1:
        over = round(tax_withheld - est_tax, 2)
        anomalies.append({
            "type": "OVER_WITHHOLDING",
            "severity": "warning",
            "title": "Potential Over-Withholding",
            "description": (
                f"Your employer withheld ${tax_withheld:,.2f} but your estimated tax liability is "
                f"${est_tax:,.2f}. You may be owed a ${over:,.2f} refund. Consider filing a T1213 "
                f"to reduce future withholdings."
            ),
            "amount": over,
        })

    # 4. Under-withholding (employer withheld less than estimated tax)
    if tax_withheld and est_tax and tax_withheld < est_tax * 0.85:
        under = round(est_tax - tax_withheld, 2)
        anomalies.append({
            "type": "UNDER_WITHHOLDING",
            "severity": "critical",
            "title": "Potential Under-Withholding",
            "description": (
                f"Your employer withheld ${tax_withheld:,.2f} but your estimated tax liability is "
                f"${est_tax:,.2f}. You may owe ${under:,.2f} when filing. Set aside funds to cover this."
            ),
            "amount": under,
        })

    # 5. Significant unused RRSP room
    if rrsp_room > 5000 and income > 50000:
        potential = round(rrsp_room * marginal, 2) if marginal > 0 else round(rrsp_room * 0.3, 2)
        anomalies.append({
            "type": "UNUSED_RRSP_ROOM",
            "severity": "info",
            "title": "Significant Unused RRSP Room",
            "description": (
                f"You have ${rrsp_room:,.0f} in unused RRSP contribution room. "
                f"Contributing could save up to ${potential:,.0f} in taxes at your current marginal rate."
            ),
            "amount": potential,
        })

    # 6. High effective tax rate (may benefit from optimization)
    if income > 0 and est_tax > 0:
        effective_rate = est_tax / income
        if effective_rate > 0.35:
            anomalies.append({
                "type": "HIGH_EFFECTIVE_RATE",
                "severity": "warning",
                "title": "High Effective Tax Rate",
                "description": (
                    f"Your effective tax rate is {effective_rate:.1%}. This is above average for your "
                    f"income level. Consider RRSP contributions, pension income splitting, or other "
                    f"deductions to reduce your rate."
                ),
                "amount": 0,
            })

    # 7. Tax rate anomaly (withholding rate seems wrong)
    if income > 0 and tax_withheld > 0:
        withholding_rate = tax_withheld / income
        if withholding_rate > 0.55:
            anomalies.append({
                "type": "TAX_RATE_ANOMALY",
                "severity": "critical",
                "title": "Unusual Withholding Rate",
                "description": (
                    f"Tax withheld is {withholding_rate:.0%} of income, which is unusually high. "
                    f"Please verify your T4 data is entered correctly."
                ),
                "amount": 0,
            })
        elif withholding_rate < 0.05 and income > 30000:
            anomalies.append({
                "type": "LOW_WITHHOLDING_RATE",
                "severity": "warning",
                "title": "Unusually Low Withholding",
                "description": (
                    f"Tax withheld is only {withholding_rate:.1%} of income (${income:,.0f}). "
                    f"This seems low and you may owe taxes when filing."
                ),
                "amount": 0,
            })

    # 8. Multiple T4 CPP/EI risk (if income suggests multiple employers)
    if cpp > 0 and income > 70000:
        from rules.cpp_ei_rates import get_max_cpp
        max_cpp = get_max_cpp(tax_year)
        if cpp > max_cpp * 0.95 and cpp <= max_cpp:
            anomalies.append({
                "type": "NEAR_CPP_MAX",
                "severity": "info",
                "title": "Near CPP Maximum",
                "description": (
                    f"Your CPP contributions (${cpp:,.2f}) are near the annual maximum (${max_cpp:,.2f}). "
                    f"If you have multiple employers, verify total contributions don't exceed the max."
                ),
                "amount": 0,
            })

    # Sort by severity
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    anomalies.sort(key=lambda x: severity_order.get(x["severity"], 2))

    return anomalies
