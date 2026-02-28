"""AI Financial Advisor service: health score, recommendations, deadlines."""
from datetime import datetime, date


# Key CRA deadlines (month, day)
DEADLINES = {
    "rrsp": (3, 3, "RRSP Contribution Deadline"),
    "tax_filing": (4, 30, "Tax Filing Deadline"),
    "tfsa": (12, 31, "TFSA Year-End"),
    "gst_q1": (7, 5, "GST/HST Credit Payment"),
    "gst_q2": (10, 5, "GST/HST Credit Payment"),
    "gst_q3": (1, 5, "GST/HST Credit Payment"),
    "gst_q4": (4, 5, "GST/HST Credit Payment"),
}


def build_advisor_data(
    profile_data: dict,
    insights: list[dict],
    action_items: list[dict],
    current_year: int,
    tax_year: int,
) -> dict:
    """Build the AI Financial Advisor payload."""
    employment = profile_data.get("employment") or {}
    registered = profile_data.get("registered_accounts") or {}
    derived = profile_data.get("derived") or {}

    income = employment.get("total_employment_income") or 0
    tax_withheld = employment.get("total_income_tax_withheld") or 0
    tax_liability = derived.get("estimated_tax_liability") or 0
    marginal_rate = derived.get("marginal_rate_combined") or 0
    effective_rate = (tax_liability / income) if income > 0 else 0

    rrsp_room = registered.get("rrsp_room_remaining") or registered.get("rrsp_deduction_limit") or 0
    rrsp_limit = registered.get("rrsp_deduction_limit") or rrsp_room
    rrsp_contributed = registered.get("rrsp_contributions") or 0
    tfsa_room = registered.get("tfsa_room_remaining") or 0
    tfsa_limit = registered.get("tfsa_limit") or (tfsa_room + (registered.get("tfsa_contributions") or 0)) or 7000
    tfsa_contributed = registered.get("tfsa_contributions") or 0

    # Financial Health Score (0-100)
    health_score = _calculate_health_score(
        rrsp_contributed, rrsp_limit,
        tfsa_contributed, tfsa_limit,
        effective_rate, marginal_rate,
        action_items,
    )

    # Last Year Summary
    last_year_summary = {
        "tax_year": tax_year,
        "income": round(income, 2),
        "tax_paid": round(tax_withheld, 2),
        "tax_liability": round(tax_liability, 2),
        "effective_rate": round(effective_rate, 4),
        "marginal_rate": round(marginal_rate, 4),
        "rrsp_contributed": round(rrsp_contributed, 2),
        "rrsp_room_remaining": round(rrsp_room, 2),
        "tfsa_contributed": round(tfsa_contributed, 2),
        "tfsa_room_remaining": round(tfsa_room, 2),
        "refund_or_owing": round(tax_withheld - tax_liability, 2),
    }

    # This Year Plan
    total_savings_opportunity = sum(i.get("estimated_value") or 0 for i in insights)
    pending_actions = sum(1 for a in action_items if a.get("status") == "pending")
    completed_actions = sum(1 for a in action_items if a.get("status") == "completed")
    upcoming_deadlines = _get_upcoming_deadlines(current_year)
    next_deadline = upcoming_deadlines[0] if upcoming_deadlines else None

    this_year_plan = {
        "current_year": current_year,
        "total_savings_opportunity": round(total_savings_opportunity, 2),
        "pending_actions": pending_actions,
        "completed_actions": completed_actions,
        "total_actions": len(action_items),
        "next_deadline": next_deadline,
    }

    # Top Recommendations (reframed insights)
    recommendations = _build_recommendations(
        insights, income, tax_liability, effective_rate, rrsp_room, tax_year, current_year
    )

    # Financial Calendar
    calendar = _build_calendar(current_year, upcoming_deadlines)

    return {
        "health_score": health_score,
        "last_year": last_year_summary,
        "this_year": this_year_plan,
        "recommendations": recommendations,
        "calendar": calendar,
    }


def _calculate_health_score(
    rrsp_contributed, rrsp_limit,
    tfsa_contributed, tfsa_limit,
    effective_rate, marginal_rate,
    action_items,
) -> dict:
    """Calculate financial health score (0-100) with component breakdown."""
    # RRSP utilization (30%)
    if rrsp_limit > 0:
        rrsp_score = min(100, (rrsp_contributed / rrsp_limit) * 100)
    else:
        rrsp_score = 50  # Neutral if no limit info

    # TFSA utilization (20%)
    if tfsa_limit > 0:
        tfsa_score = min(100, (tfsa_contributed / tfsa_limit) * 100)
    else:
        tfsa_score = 50

    # Tax efficiency (30%) — lower effective rate relative to marginal = better
    if marginal_rate > 0:
        tax_efficiency = max(0, 100 - (effective_rate / marginal_rate * 100))
    else:
        tax_efficiency = 50

    # Action completion (20%)
    total_items = len(action_items)
    completed_items = sum(1 for a in action_items if a.get("status") == "completed")
    action_score = (completed_items / total_items * 100) if total_items > 0 else 50

    overall = round(
        rrsp_score * 0.30 +
        tfsa_score * 0.20 +
        tax_efficiency * 0.30 +
        action_score * 0.20,
        1,
    )

    return {
        "overall": min(100, max(0, overall)),
        "components": {
            "rrsp_utilization": round(rrsp_score, 1),
            "tfsa_utilization": round(tfsa_score, 1),
            "tax_efficiency": round(tax_efficiency, 1),
            "action_completion": round(action_score, 1),
        },
    }


def _build_recommendations(
    insights, income, tax_liability, effective_rate, rrsp_room, tax_year, current_year
) -> list[dict]:
    """Build top-5 recommendations with last_year/this_year framing."""
    sorted_insights = sorted(
        insights, key=lambda x: x.get("estimated_value") or 0, reverse=True
    )

    recommendations = []
    for ins in sorted_insights[:5]:
        est = ins.get("estimated_value") or 0
        category = ins.get("category", "THIS_YEAR")

        # Determine deadline based on category
        if category == "ACT_NOW":
            deadline = f"{current_year}-03-03"
            priority = "HIGH"
            urgency = "ACT_NOW"
        elif category == "THIS_YEAR":
            deadline = f"{current_year}-12-31"
            priority = ins.get("priority", "MEDIUM")
            urgency = "THIS_YEAR"
        else:
            deadline = None
            priority = ins.get("priority", "LOW")
            urgency = "LONG_TERM"

        recommendations.append({
            "insight_id": ins.get("id", ""),
            "last_year": f"In {tax_year}, you earned ${income:,.0f} and paid ${tax_liability:,.0f} in taxes ({effective_rate:.1%} effective rate)",
            "this_year": ins.get("headline", ""),
            "detail": ins.get("detail", ""),
            "action_required": ins.get("action_required", ""),
            "deadline": deadline,
            "estimated_value": est,
            "priority": priority,
            "urgency": urgency,
        })

    return recommendations


def _get_upcoming_deadlines(current_year: int) -> list[dict]:
    """Get upcoming CRA deadlines sorted by date."""
    now = datetime.now().date()
    deadlines = []

    for key, (month, day, label) in DEADLINES.items():
        try:
            d = date(current_year, month, day)
        except ValueError:
            continue
        if d >= now:
            days_away = (d - now).days
            if days_away <= 7:
                urgency = "critical"
            elif days_away <= 30:
                urgency = "warning"
            else:
                urgency = "info"
            deadlines.append({
                "key": key,
                "label": label,
                "date": d.isoformat(),
                "days_away": days_away,
                "urgency": urgency,
            })

    deadlines.sort(key=lambda x: x["date"])
    return deadlines


def _build_calendar(current_year: int, upcoming_deadlines: list[dict]) -> list[dict]:
    """Build financial calendar for the year with all key dates."""
    all_dates = []
    for key, (month, day, label) in DEADLINES.items():
        try:
            d = date(current_year, month, day)
        except ValueError:
            continue
        now = datetime.now().date()
        days_away = (d - now).days
        status = "past" if d < now else "upcoming"
        if status == "upcoming":
            if days_away <= 7:
                urgency = "critical"
            elif days_away <= 30:
                urgency = "warning"
            else:
                urgency = "info"
        else:
            urgency = "past"

        all_dates.append({
            "key": key,
            "label": label,
            "date": d.isoformat(),
            "month": d.strftime("%b"),
            "day": d.day,
            "status": status,
            "urgency": urgency,
            "days_away": days_away if status == "upcoming" else None,
        })

    all_dates.sort(key=lambda x: x["date"])
    return all_dates
