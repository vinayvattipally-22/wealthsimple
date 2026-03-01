"""Convert insights into dated, trackable action items."""
from datetime import datetime, timedelta


# RRSP deadline: March 3 of the year after the tax year (or Feb 29 in leap years)
def _rrsp_deadline(tax_year: int) -> datetime:
    return datetime(tax_year + 1, 3, 3)


def _filing_deadline(tax_year: int) -> datetime:
    return datetime(tax_year + 1, 4, 30)


def generate_action_items(
    insights: list[dict],
    profile_data: dict,
    tax_year: int,
) -> list[dict]:
    """
    Convert analysis insights into concrete action items with deadlines.

    Rules:
    - ACT_NOW → deadline = RRSP deadline or 7 days from now (whichever sooner)
    - THIS_YEAR → deadline = Dec 31 of the tax year
    - LONG_TERM → no deadline (ongoing)
    """
    now = datetime.utcnow()
    rrsp_dl = _rrsp_deadline(tax_year)
    filing_dl = _filing_deadline(tax_year)
    items = []

    for ins in insights:
        category = ins.get("category", "THIS_YEAR")
        insight_type = ins.get("id", "")
        action_text = ins.get("action_required") or ins.get("headline", "")
        headline = ins.get("headline", "")
        detail = ins.get("detail", "")

        # Skip if no actionable text
        if not action_text:
            continue

        # Determine deadline based on category and insight type
        if category == "ACT_NOW":
            # Time-sensitive: use RRSP deadline or 7 days, whichever is sooner
            seven_days = now + timedelta(days=7)
            if "RRSP" in insight_type or "rrsp" in action_text.lower():
                deadline = min(rrsp_dl, seven_days)
            elif "filing" in action_text.lower() or "file" in action_text.lower():
                deadline = min(filing_dl, seven_days)
            else:
                deadline = seven_days
        elif category == "THIS_YEAR":
            deadline = datetime(tax_year, 12, 31)
        else:
            deadline = None  # LONG_TERM — ongoing

        items.append({
            "title": action_text[:512],
            "description": f"{headline}\n\n{detail}".strip() if detail else headline,
            "deadline": deadline.isoformat() if deadline else None,
            "priority": ins.get("priority", "MEDIUM"),
            "status": "pending",
            "estimated_value": ins.get("estimated_value") or 0,
            "insight_type": insight_type,
        })

    # Sort: HIGH priority first, then by deadline (soonest first, None last)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    items.sort(key=lambda x: (
        priority_order.get(x["priority"], 1),
        x["deadline"] or "9999-12-31",
    ))

    return items


def prioritize_actions(action_items: list[dict]) -> list[dict]:
    """AI-powered action prioritization: score each item and add reasoning.

    Returns the same list with added ``ai_score`` (0-100) and ``ai_reasoning`` fields,
    sorted by score descending.
    """
    now = datetime.utcnow()

    for item in action_items:
        score = 0
        reasons = []

        # Value factor (0-40 points)
        value = item.get("estimated_value") or 0
        if value > 5000:
            score += 40
            reasons.append("High dollar impact")
        elif value > 1000:
            score += 25
            reasons.append("Moderate savings potential")
        elif value > 0:
            score += 10
            reasons.append("Some savings potential")

        # Urgency factor (0-30 points)
        deadline = item.get("deadline")
        if deadline:
            try:
                dl = datetime.fromisoformat(str(deadline).replace("Z", "+00:00")) if isinstance(deadline, str) else deadline
                days_left = (dl - now).days
                if days_left < 0:
                    score += 30
                    reasons.append("OVERDUE")
                elif days_left <= 7:
                    score += 25
                    reasons.append("Due this week")
                elif days_left <= 30:
                    score += 15
                    reasons.append("Due this month")
                else:
                    score += 5
            except (ValueError, TypeError):
                pass

        # Priority factor (0-20 points)
        priority = item.get("priority", "MEDIUM")
        if priority == "HIGH":
            score += 20
            reasons.append("High priority")
        elif priority == "MEDIUM":
            score += 10

        # Ease factor (0-10 points)
        title_lower = (item.get("title") or "").lower()
        if any(kw in title_lower for kw in ["contribute", "open", "transfer", "deposit"]):
            score += 10
            reasons.append("Easy to implement")
        elif any(kw in title_lower for kw in ["review", "check", "verify"]):
            score += 7

        item["ai_score"] = min(score, 100)
        item["ai_reasoning"] = " | ".join(reasons[:3])

    action_items.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
    return action_items
