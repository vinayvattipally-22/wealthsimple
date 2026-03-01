"""Background scheduler for periodic stock news fetching using APScheduler."""
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _refresh_all_tracked_stocks():
    """Job: iterate active TrackedStocks, fetch news if due, score and generate insights."""
    from database.session import AsyncSessionLocal
    from database.models import TrackedStock
    from sqlalchemy import select
    from services.stock_news_service import fetch_and_store_news, score_unanalyzed_news
    from services.stock_insight_service import generate_insights, should_regenerate_insights

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TrackedStock).where(TrackedStock.is_active == True)
        )
        tracked = result.scalars().all()

        for stock in tracked:
            now = datetime.utcnow()
            interval = timedelta(hours=stock.news_fetch_interval_hours or 4)

            if stock.last_news_fetch and (now - stock.last_news_fetch) < interval:
                continue

            try:
                new_articles = await fetch_and_store_news(stock.ticker, db)
                if new_articles:
                    await score_unanalyzed_news(stock.ticker, db)

                if await should_regenerate_insights(stock.ticker, db):
                    await generate_insights(
                        stock.ticker, stock.company_name or stock.ticker, db
                    )

                logger.info(
                    f"Refreshed {stock.ticker}: {len(new_articles)} new articles"
                )
            except Exception as e:
                logger.error(f"Failed to refresh {stock.ticker}: {e}")


def start_scheduler():
    """Start the background scheduler with configurable interval."""
    interval_hours = int(os.getenv("NEWS_REFRESH_INTERVAL_HOURS", "4"))

    scheduler.add_job(
        _refresh_all_tracked_stocks,
        trigger=IntervalTrigger(hours=interval_hours),
        id="refresh_tracked_stocks",
        name="Refresh tracked stock news",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"News scheduler started: refresh every {interval_hours}h")


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("News scheduler stopped")
