"""Stock news & insights endpoints: news feed, refresh, insights, generation."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.models import User, StockNews, StockInsight
from middleware.auth import get_current_user
from middleware.rate_limiter import limiter, READ_LIMIT, ANALYSIS_LIMIT

router = APIRouter()

DISCLAIMER = (
    "The insights provided here are AI-generated observations based on publicly "
    "available market data and news. They do not constitute financial advice, "
    "investment recommendations, or solicitations to buy, sell, or hold any "
    "securities. The app and its creators assume no responsibility for investment "
    "decisions made based on these insights. Always conduct your own research and "
    "consult a qualified financial advisor before making investment decisions."
)


@router.get("/{ticker}/news")
@limiter.limit(READ_LIMIT)
async def get_stock_news(
    request: Request,
    ticker: str,
    limit: int = Query(default=30, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get stored news for a ticker, paginated by published_at DESC.

    If no news exists yet, triggers an initial fetch.
    """
    from services.stock_news_service import get_news_for_ticker, fetch_and_store_news

    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 16:
        raise HTTPException(400, "Invalid ticker")

    articles, total = await get_news_for_ticker(ticker, db, limit, offset)

    # Auto-fetch if no news stored yet
    if total == 0 and offset == 0:
        new_articles = await fetch_and_store_news(ticker, db)
        if new_articles:
            articles, total = await get_news_for_ticker(ticker, db, limit, offset)

    return {
        "news": [
            {
                "id": a.id,
                "ticker": a.ticker,
                "title": a.title,
                "url": a.url,
                "publisher": a.publisher,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "source": a.source,
                "sentiment_score": a.sentiment_score,
                "sentiment_label": a.sentiment_label,
                "summary": a.summary,
                "is_analyzed": a.is_analyzed,
            }
            for a in articles
        ],
        "total": total,
        "ticker": ticker,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{ticker}/news/refresh")
@limiter.limit(ANALYSIS_LIMIT)
async def refresh_stock_news(
    request: Request,
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force a fresh news fetch + sentiment scoring for a ticker."""
    from services.stock_news_service import (
        fetch_and_store_news,
        score_unanalyzed_news,
        ensure_tracked,
    )

    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 16:
        raise HTTPException(400, "Invalid ticker")

    await ensure_tracked(ticker, "", db)
    new_articles = await fetch_and_store_news(ticker, db)
    scored = await score_unanalyzed_news(ticker, db)

    return {
        "new_articles": len(new_articles),
        "scored": scored,
        "ticker": ticker,
    }


@router.get("/{ticker}/insights")
@limiter.limit(READ_LIMIT)
async def get_stock_insights(
    request: Request,
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get latest insights (short/mid/long) for a ticker with referenced news articles."""
    from services.stock_insight_service import get_latest_insights

    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 16:
        raise HTTPException(400, "Invalid ticker")

    all_insights = await get_latest_insights(ticker, db)

    # Check if any are pending review
    review_pending = any(i.review_status == "PENDING" for i in all_insights) if all_insights else False

    # Only show APPROVED insights to users
    insights = [i for i in all_insights if i.review_status == "APPROVED"]

    if not insights:
        return {
            "insights": [],
            "generated_at": None,
            "ticker": ticker,
            "disclaimer": DISCLAIMER,
            "review_pending": review_pending,
        }

    # Collect all referenced article IDs to fetch their details
    all_article_ids = set()
    for ins in insights:
        for aid in (ins.news_article_ids or []):
            all_article_ids.add(aid)

    # Fetch referenced articles
    articles_map = {}
    if all_article_ids:
        result = await db.execute(
            select(StockNews).where(StockNews.id.in_(all_article_ids))
        )
        for a in result.scalars().all():
            articles_map[a.id] = {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "publisher": a.publisher,
                "sentiment_score": a.sentiment_score,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }

    return {
        "insights": [
            {
                "id": ins.id,
                "timeframe": ins.timeframe,
                "direction": ins.direction,
                "confidence": ins.confidence,
                "reasoning": ins.reasoning,
                "referenced_articles": [
                    articles_map[aid]
                    for aid in (ins.news_article_ids or [])
                    if aid in articles_map
                ],
                "created_at": ins.created_at.isoformat() if ins.created_at else None,
            }
            for ins in insights
        ],
        "generated_at": insights[0].created_at.isoformat() if insights else None,
        "ticker": ticker,
        "disclaimer": DISCLAIMER,
        "review_pending": review_pending,
    }


@router.post("/{ticker}/insights/generate")
@limiter.limit(ANALYSIS_LIMIT)
async def generate_stock_insights(
    request: Request,
    ticker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger insight generation from stored news. Requires 3+ news articles."""
    from services.stock_insight_service import generate_insights
    from services.stock_news_service import get_news_for_ticker

    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 16:
        raise HTTPException(400, "Invalid ticker")

    # Check we have enough news
    _, total = await get_news_for_ticker(ticker, db, limit=1, offset=0)
    if total < 3:
        raise HTTPException(
            400,
            f"Need at least 3 news articles to generate insights (have {total}). "
            "Try refreshing news first.",
        )

    insights = await generate_insights(ticker, "", db, force=True)

    if not insights:
        raise HTTPException(500, "Insight generation failed")

    return {
        "insights": [
            {
                "id": ins.id,
                "timeframe": ins.timeframe,
                "direction": ins.direction,
                "confidence": ins.confidence,
                "reasoning": ins.reasoning,
                "news_article_ids": ins.news_article_ids,
                "created_at": ins.created_at.isoformat() if ins.created_at else None,
            }
            for ins in insights
        ],
        "generated_at": insights[0].created_at.isoformat() if insights else None,
        "ticker": ticker,
        "disclaimer": DISCLAIMER,
    }
