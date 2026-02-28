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
