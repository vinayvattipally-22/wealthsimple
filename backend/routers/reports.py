"""PDF report generation endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.models import FinancialProfile, Insight
from services.report_service import generate_pdf_report
from middleware.rate_limiter import limiter, READ_LIMIT
import io

router = APIRouter()


@router.get("/reports/{profile_id}/pdf")
@limiter.limit(READ_LIMIT)
async def download_report(request: Request, profile_id: int, db: AsyncSession = Depends(get_db)):
    """Generate and download PDF report for a profile's approved insights."""
    profile = await db.get(FinancialProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    result = await db.execute(
        select(Insight).where(
            Insight.profile_id == profile_id,
            Insight.review_status == "APPROVED",
        )
    )
    insights = result.scalars().all()

    profile_data = profile.profile_data or {}
    insights_list = [
        {
            "priority": i.priority,
            "category": i.category,
            "headline": i.headline,
            "detail": i.detail,
            "estimated_value": i.estimated_value,
            "action_required": i.action_required,
            "product_link": i.product_link,
        }
        for i in insights
    ]

    total_savings = sum(i.estimated_value or 0 for i in insights)
    summary = {
        "total_identified_savings": total_savings,
        "act_now_count": sum(1 for i in insights if i.category == "ACT_NOW"),
        "this_year_count": sum(1 for i in insights if i.category == "THIS_YEAR"),
        "long_term_count": sum(1 for i in insights if i.category == "LONG_TERM"),
    }

    pdf_bytes = generate_pdf_report(profile_data, insights_list, summary)
    year = profile.tax_year or 2024
    filename = f"tax_insights_{year}_profile_{profile_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
