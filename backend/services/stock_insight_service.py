"""Stock insight service: LLM-powered multi-timeframe price direction insights."""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import StockNews, StockInsight

logger = logging.getLogger(__name__)

INSIGHT_COOLDOWN_HOURS = 2
INSIGHT_STALE_HOURS = 6
NEW_ARTICLES_THRESHOLD = 3


async def generate_insights(
    ticker: str,
    company_name: str,
    db: AsyncSession,
    force: bool = False,
) -> list[StockInsight]:
    """Generate short/mid/long term insights from stored news + market data.

    Skips generation if recent insights exist (< INSIGHT_COOLDOWN_HOURS) unless force=True.
    Returns list of 3 new StockInsight rows.
    """
    from services.llm_service import _build_system_message, _build_user_message, _call_chat
    from prompts.stock_news_prompts import PRICE_INSIGHT_PROMPT
    from services.stock_data_service import fetch_market_data

    ticker = ticker.upper().strip()

    # Check cooldown
    if not force:
        latest = await _get_latest_insight_time(ticker, db)
        if latest and (datetime.utcnow() - latest) < timedelta(hours=INSIGHT_COOLDOWN_HOURS):
            return await get_latest_insights(ticker, db)

    # Fetch recent news (last 30 days)
    cutoff_30d = datetime.utcnow() - timedelta(days=30)
    cutoff_90d = datetime.utcnow() - timedelta(days=90)

    recent_result = await db.execute(
        select(StockNews)
        .where(StockNews.ticker == ticker, StockNews.published_at >= cutoff_30d)
        .order_by(StockNews.published_at.desc())
        .limit(30)
    )
    recent_news = list(recent_result.scalars().all())

    # Fetch older news (30-90 days ago)
    historical_result = await db.execute(
        select(StockNews)
        .where(
            StockNews.ticker == ticker,
            StockNews.published_at >= cutoff_90d,
            StockNews.published_at < cutoff_30d,
        )
        .order_by(StockNews.published_at.desc())
        .limit(20)
    )
    historical_news = list(historical_result.scalars().all())

    if not recent_news and not historical_news:
        return []

    # Fetch current market data for price context
    try:
        market_data = await fetch_market_data(ticker)
        current_price = market_data.get("current_price", 0)
        week_52_high = market_data.get("fifty_two_week_high", 0)
        week_52_low = market_data.get("fifty_two_week_low", 0)
        price_history = market_data.get("price_history", [])

        # Calculate price changes
        price_change_30d = 0
        price_change_90d = 0
        if price_history and current_price:
            if len(price_history) >= 22:
                p30 = price_history[-22]["close"]
                price_change_30d = ((current_price - p30) / p30) * 100 if p30 else 0
            if len(price_history) >= 63:
                p90 = price_history[-63]["close"]
                price_change_90d = ((current_price - p90) / p90) * 100 if p90 else 0
    except Exception:
        current_price = 0
        week_52_high = 0
        week_52_low = 0
        price_change_30d = 0
        price_change_90d = 0

    # Build LLM input
    llm_data = {
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "week_52_high": week_52_high,
        "week_52_low": week_52_low,
        "price_change_30d_pct": round(price_change_30d, 2),
        "price_change_90d_pct": round(price_change_90d, 2),
        "recent_news": [
            {
                "id": a.id,
                "title": a.title,
                "sentiment_score": a.sentiment_score,
                "sentiment_label": a.sentiment_label,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in recent_news
        ],
        "historical_news": [
            {
                "id": a.id,
                "title": a.title,
                "sentiment_score": a.sentiment_score,
                "sentiment_label": a.sentiment_label,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in historical_news
        ],
    }

    def _call():
        sys = _build_system_message(PRICE_INSIGHT_PROMPT)
        user = _build_user_message(PRICE_INSIGHT_PROMPT, llm_data)
        raw = _call_chat(sys, user, PRICE_INSIGHT_PROMPT.get("settingsJson"))
        return json.loads(raw) if isinstance(raw, str) else raw

    try:
        result = await asyncio.to_thread(_call)
    except Exception as e:
        logger.error(f"LLM insight generation failed for {ticker}: {e}")
        return []

    # Create 3 insight rows
    now = datetime.utcnow()
    insights = []
    for timeframe in ("short", "mid", "long"):
        tf_key = f"{timeframe}_term"
        tf_data = result.get(tf_key, {})
        if not tf_data:
            continue

        insight = StockInsight(
            ticker=ticker,
            company_name=company_name,
            timeframe=timeframe,
            direction=tf_data.get("direction", "neutral"),
            confidence=tf_data.get("confidence", 0.5),
            reasoning=tf_data.get("reasoning", ""),
            news_article_ids=tf_data.get("key_article_ids", []),
            created_at=now,
        )
        db.add(insight)
        insights.append(insight)

    await db.commit()
    for ins in insights:
        await db.refresh(ins)

    return insights


async def get_latest_insights(ticker: str, db: AsyncSession) -> list[StockInsight]:
    """Get the most recent set of insights (3 rows) for a ticker."""
    ticker = ticker.upper().strip()
    result = await db.execute(
        select(StockInsight)
        .where(StockInsight.ticker == ticker)
        .order_by(StockInsight.created_at.desc())
        .limit(3)
    )
    return list(result.scalars().all())


async def get_insight_history(
    ticker: str, db: AsyncSession, limit: int = 10
) -> list[dict]:
    """Get historical insight snapshots grouped by created_at."""
    ticker = ticker.upper().strip()
    result = await db.execute(
        select(StockInsight)
        .where(StockInsight.ticker == ticker)
        .order_by(StockInsight.created_at.desc())
        .limit(limit * 3)  # 3 rows per generation
    )
    all_insights = list(result.scalars().all())

    # Group by created_at timestamp
    groups = {}
    for ins in all_insights:
        key = ins.created_at.isoformat() if ins.created_at else "unknown"
        if key not in groups:
            groups[key] = []
        groups[key].append(ins)

    return [
        {
            "generated_at": key,
            "insights": [
                {
                    "timeframe": i.timeframe,
                    "direction": i.direction,
                    "confidence": i.confidence,
                }
                for i in items
            ],
        }
        for key, items in list(groups.items())[:limit]
    ]


async def should_regenerate_insights(ticker: str, db: AsyncSession) -> bool:
    """Check if new insights should be generated based on new articles and staleness."""
    ticker = ticker.upper().strip()

    latest_time = await _get_latest_insight_time(ticker, db)

    # No insights exist yet
    if not latest_time:
        # Only generate if we have at least some news
        count_result = await db.execute(
            select(func.count(StockNews.id)).where(StockNews.ticker == ticker)
        )
        return (count_result.scalar() or 0) >= NEW_ARTICLES_THRESHOLD

    # Insights are stale (> INSIGHT_STALE_HOURS)
    if (datetime.utcnow() - latest_time) > timedelta(hours=INSIGHT_STALE_HOURS):
        return True

    # New articles since last insight generation
    new_count_result = await db.execute(
        select(func.count(StockNews.id)).where(
            StockNews.ticker == ticker,
            StockNews.fetched_at > latest_time,
        )
    )
    new_count = new_count_result.scalar() or 0
    return new_count >= NEW_ARTICLES_THRESHOLD


async def _get_latest_insight_time(ticker: str, db: AsyncSession) -> datetime | None:
    """Get the created_at of the most recent insight for a ticker."""
    result = await db.execute(
        select(StockInsight.created_at)
        .where(StockInsight.ticker == ticker.upper())
        .order_by(StockInsight.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row
