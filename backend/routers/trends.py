"""Multi-year trend analysis: aggregate profiles across tax years."""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.models import FinancialProfile, Insight
from middleware.rate_limiter import limiter, READ_LIMIT

from services.tax_engine import estimated_liability, combined_marginal_rate

router = APIRouter()


@router.get("/trends")
@limiter.limit(READ_LIMIT)
async def get_trends(
    request: Request,
    user_id: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Return multi-year trend data aggregated from all profiles."""
    query = select(FinancialProfile).order_by(FinancialProfile.tax_year.asc())
    if user_id:
        query = query.where(FinancialProfile.user_id == user_id)

    result = await db.execute(query)
    profiles = result.scalars().all()
    if not profiles:
        return {"years": [], "income": [], "tax_paid": [], "effective_rate": [], "savings": [], "yoy_growth": []}

    years = []
    income_list = []
    tax_paid_list = []
    effective_rate_list = []
    savings_list = []

    for profile in profiles:
        data = profile.profile_data or {}
        employment = data.get("employment", {})
        income = employment.get("total_employment_income") or 0
        province = profile.province_code or "ON"
        year = profile.tax_year

        # Compute tax liability
        liability = estimated_liability(income, province, year) if income > 0 else 0
        eff_rate = (liability / income) if income > 0 else 0

        # Get savings from advisor-approved insights only
        from database.queries import approved_insights_query

        ins_result = await db.execute(approved_insights_query(profile_id=profile.id))
        insights = ins_result.scalars().all()
        total_savings = sum(i.estimated_value or 0 for i in insights)

        years.append(year)
        income_list.append(round(income, 2))
        tax_paid_list.append(round(liability, 2))
        effective_rate_list.append(round(eff_rate, 4))
        savings_list.append(round(total_savings, 2))

    # Compute YoY growth
    yoy_growth = [None]
    for i in range(1, len(income_list)):
        prev = income_list[i - 1]
        if prev > 0:
            yoy_growth.append(round((income_list[i] - prev) / prev * 100, 1))
        else:
            yoy_growth.append(None)

    return {
        "years": years,
        "income": income_list,
        "tax_paid": tax_paid_list,
        "effective_rate": effective_rate_list,
        "savings": savings_list,
        "yoy_growth": yoy_growth,
    }
