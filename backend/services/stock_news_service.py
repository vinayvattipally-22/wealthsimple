"""Stock news service: fetch, store, deduplicate, and score news articles."""
import json
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from database.models import StockNews, TrackedStock

logger = logging.getLogger(__name__)


async def fetch_and_store_news(ticker: str, db: AsyncSession) -> list[StockNews]:
    """Fetch news via yfinance/Alpha Vantage and store new articles in DB.

    Deduplicates by (ticker, title, published_at). Returns only newly inserted articles.
    """
    from services.stock_data_service import fetch_news

    ticker = ticker.upper().strip()
    raw_items = await fetch_news(ticker)

    if not raw_items:
        return []

    new_articles = []
    for item in raw_items:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        # Parse published date
        published_at = None
        pub_raw = item.get("published") or item.get("providerPublishTime")
        if pub_raw:
            if isinstance(pub_raw, (int, float)):
                published_at = datetime.utcfromtimestamp(pub_raw)
            elif isinstance(pub_raw, str):
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y%m%dT%H%M%S", "%Y-%m-%d"):
                    try:
                        published_at = datetime.strptime(pub_raw, fmt)
                        break
                    except ValueError:
                        continue

        # Determine source
        source = "alpha_vantage" if item.get("source") == "alpha_vantage" else "yfinance"

        # Pre-scored sentiment from Alpha Vantage
        av_score = item.get("sentiment_score")
        av_label = item.get("sentiment_label")
        is_analyzed = av_score is not None

        # Check for duplicate before inserting
        existing = await db.execute(
            select(StockNews).where(
                StockNews.ticker == ticker,
                StockNews.title == title,
                StockNews.published_at == published_at,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            continue

        article = StockNews(
            ticker=ticker,
            title=title,
            url=item.get("link") or item.get("url"),
            publisher=item.get("publisher"),
            published_at=published_at,
            source=source,
            sentiment_score=float(av_score) if av_score is not None else None,
            sentiment_label=av_label,
            is_analyzed=is_analyzed,
        )
        db.add(article)
        new_articles.append(article)

    if new_articles:
        await db.flush()

    # Update TrackedStock.last_news_fetch
    result = await db.execute(
        select(TrackedStock).where(TrackedStock.ticker == ticker)
    )
    tracked = result.scalar_one_or_none()
    if tracked:
        tracked.last_news_fetch = datetime.utcnow()

    await db.commit()
    return new_articles


async def score_unanalyzed_news(ticker: str, db: AsyncSession) -> int:
    """Score unanalyzed articles using LLM batch sentiment analysis.

    Returns count of articles scored.
    """
    from services.llm_service import _build_system_message, _build_user_message, _call_chat
    from prompts.stock_news_prompts import NEWS_SENTIMENT_BATCH_PROMPT

    result = await db.execute(
        select(StockNews).where(
            StockNews.ticker == ticker.upper(),
            StockNews.is_analyzed == False,
        ).order_by(StockNews.published_at.desc()).limit(20)
    )
    articles = list(result.scalars().all())

    if not articles:
        return 0

    # Build batch for LLM
    batch_data = {
        "ticker": ticker.upper(),
        "articles": [
            {"index": i, "title": a.title, "publisher": a.publisher or "Unknown"}
            for i, a in enumerate(articles)
        ],
    }

    def _call():
        sys = _build_system_message(NEWS_SENTIMENT_BATCH_PROMPT)
        user = _build_user_message(NEWS_SENTIMENT_BATCH_PROMPT, batch_data)
        raw = _call_chat(sys, user, NEWS_SENTIMENT_BATCH_PROMPT.get("settingsJson"))
        return json.loads(raw) if isinstance(raw, str) else raw

    try:
        result_data = await asyncio.to_thread(_call)
    except Exception as e:
        logger.error(f"LLM sentiment scoring failed for {ticker}: {e}")
        return 0

    scored_articles = result_data.get("scored_articles", [])
    scored_count = 0

    for scored in scored_articles:
        idx = scored.get("index")
        if idx is not None and 0 <= idx < len(articles):
            article = articles[idx]
            article.sentiment_score = scored.get("sentiment_score", 0.0)
            article.sentiment_label = scored.get("sentiment_label", "neutral")
            article.summary = scored.get("summary", "")
            article.is_analyzed = True
            scored_count += 1

    await db.commit()
    return scored_count


async def get_news_for_ticker(
    ticker: str,
    db: AsyncSession,
    limit: int = 30,
    offset: int = 0,
) -> tuple[list[StockNews], int]:
    """Get paginated news for a ticker, sorted by published_at DESC."""
    ticker = ticker.upper().strip()

    # Total count
    count_result = await db.execute(
        select(func.count(StockNews.id)).where(StockNews.ticker == ticker)
    )
    total = count_result.scalar() or 0

    # Paginated results
    result = await db.execute(
        select(StockNews)
        .where(StockNews.ticker == ticker)
        .order_by(StockNews.published_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    articles = list(result.scalars().all())

    return articles, total


async def ensure_tracked(ticker: str, company_name: str, db: AsyncSession) -> TrackedStock | None:
    """Upsert into TrackedStock. Returns existing or newly created row.

    Enforces MAX_TRACKED_STOCKS limit (default 2) to control API costs.
    Returns None if the limit is reached and this is a new ticker.
    """
    import os
    max_tracked = int(os.getenv("MAX_TRACKED_STOCKS", "2"))
    ticker = ticker.upper().strip()

    result = await db.execute(
        select(TrackedStock).where(TrackedStock.ticker == ticker)
    )
    tracked = result.scalar_one_or_none()

    if tracked:
        if not tracked.is_active:
            tracked.is_active = True
        if company_name and not tracked.company_name:
            tracked.company_name = company_name
        await db.commit()
        return tracked

    # Check limit before adding a new tracked stock
    count_result = await db.execute(
        select(func.count(TrackedStock.id)).where(TrackedStock.is_active == True)
    )
    active_count = count_result.scalar() or 0
    if active_count >= max_tracked:
        return None  # Limit reached

    tracked = TrackedStock(
        ticker=ticker,
        company_name=company_name,
        is_active=True,
    )
    db.add(tracked)
    await db.commit()
    await db.refresh(tracked)
    return tracked
