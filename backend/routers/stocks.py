"""Stock research endpoints: search, SSE streaming pipeline, history, detail, backtest."""
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.models import User, StockResearch
from middleware.auth import get_current_user
from middleware.rate_limiter import limiter, READ_LIMIT, ANALYSIS_LIMIT
from services.auth_service import decode_token

router = APIRouter()

# Agent identity metadata for each pipeline stage
STOCK_AGENT_DEFS = {
    "market_data": {
        "agent_name": "Market Data Agent",
        "agent_description": "Fetches stock price, company info, and financials",
    },
    "technical": {
        "agent_name": "Technical Analyst",
        "agent_description": "Computes SMA, RSI, MACD, Bollinger Bands",
    },
    "sentiment": {
        "agent_name": "Sentiment Analyst",
        "agent_description": "Analyzes recent news for market sentiment",
    },
    "geo_policy": {
        "agent_name": "Geo-Policy Analyst",
        "agent_description": "Assesses political and regulatory impact",
    },
    "volatility": {
        "agent_name": "Risk Analyst",
        "agent_description": "Computes volatility metrics and risk assessment",
    },
    "signal": {
        "agent_name": "Outlook Aggregator",
        "agent_description": "Combines all analyses into a market outlook",
    },
}


def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _sse_stage(stage: str, status: str, message: str) -> str:
    """Format a stage SSE event with agent metadata."""
    agent = STOCK_AGENT_DEFS.get(stage, {})
    return _sse("stage", {
        "stage": stage,
        "status": status,
        "message": message,
        "agent_name": agent.get("agent_name", stage),
        "agent_description": agent.get("agent_description", ""),
    })


async def _get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """Validate JWT token passed as query param (for SSE endpoints)."""
    if not token:
        return None
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = int(payload["sub"])
    return await db.get(User, user_id)


@router.get("/search")
@limiter.limit(READ_LIMIT)
async def search_stocks(
    request: Request,
    q: str = Query(..., min_length=1, max_length=50),
    user: User = Depends(get_current_user),
):
    """Search for stock tickers by name or symbol."""
    from services.stock_data_service import search_ticker
    results = await search_ticker(q)
    return {"results": results, "query": q}


async def _store_news_background(ticker: str, company_name: str):
    """Background: store fetched news in DB and register ticker for tracking."""
    try:
        from database.session import AsyncSessionLocal
        from services.stock_news_service import ensure_tracked, fetch_and_store_news
        async with AsyncSessionLocal() as db:
            await ensure_tracked(ticker, company_name, db)
            await fetch_and_store_news(ticker, db)
    except Exception:
        pass  # Non-critical — don't break the SSE pipeline


@router.get("/research/{ticker}/stream")
async def stream_research(
    ticker: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Stream 6-agent stock research pipeline via SSE.

    Auth via query param ?token=... since EventSource doesn't support headers.
    """
    user = await _get_user_from_token(token, db)
    if not user:
        raise HTTPException(401, "Invalid or missing token")

    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 16:
        raise HTTPException(400, "Invalid ticker")

    async def event_generator():
        from services.stock_data_service import fetch_market_data, fetch_news
        from services.technical_analysis import compute_indicators, compute_volatility_risk
        from services.stock_llm_service import analyze_news_sentiment, analyze_geo_policy, aggregate_signal

        # Stage 1: Market Data
        yield _sse_stage("market_data", "running", f"Fetching market data for {ticker}...")
        try:
            market_data = await fetch_market_data(ticker)
        except Exception as e:
            yield _sse("error", {"message": f"Failed to fetch market data for {ticker}: {str(e)}"})
            return
        company_name = market_data.get("company_name", ticker)
        current_price = market_data.get("current_price")
        yield _sse_stage("market_data", "complete", f"{company_name} — ${current_price:,.2f}" if current_price else f"{company_name} data loaded")
        yield _sse("market_data", {
            "company_name": company_name,
            "sector": market_data.get("sector"),
            "market_cap": market_data.get("market_cap"),
            "current_price": current_price,
            "currency": market_data.get("currency"),
            "52w_high": market_data.get("fifty_two_week_high"),
            "52w_low": market_data.get("fifty_two_week_low"),
            "financials": market_data.get("financials"),
            "dividends": market_data.get("dividends"),
        })
        await asyncio.sleep(0.1)

        # Fetch news (needed by sentiment + geo_policy)
        news_items = await fetch_news(ticker)

        # Background: store news in DB and register ticker for scheduled refresh
        asyncio.create_task(_store_news_background(ticker, company_name))

        # Stage 2: Technical Analysis
        yield _sse_stage("technical", "running", "Computing technical indicators...")
        price_history = market_data.get("price_history", [])
        technicals = compute_indicators(price_history)
        trend = technicals.get("trend_summary", "neutral")
        rsi = technicals.get("rsi_14", "N/A")
        yield _sse_stage("technical", "complete", f"Trend: {trend} | RSI: {rsi}")
        yield _sse("indicators", technicals)
        await asyncio.sleep(0.1)

        # Stage 3 & 4: Sentiment + Geo-Policy (run in parallel)
        yield _sse_stage("sentiment", "running", f"Analyzing {len(news_items)} news articles...")
        yield _sse_stage("geo_policy", "running", "Assessing geopolitical and regulatory risks...")

        sentiment_task = asyncio.create_task(
            analyze_news_sentiment(ticker, company_name, news_items)
        )
        geo_task = asyncio.create_task(
            analyze_geo_policy(ticker, company_name, market_data.get("sector", ""), news_items)
        )

        try:
            sentiment_result = await sentiment_task
        except Exception:
            sentiment_result = {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "key_themes": ["Analysis unavailable"],
                "articles": [],
                "summary": "Sentiment analysis could not be completed.",
            }
        sentiment_label = sentiment_result.get("overall_sentiment", "neutral")
        sentiment_score = sentiment_result.get("sentiment_score", 0)
        yield _sse_stage("sentiment", "complete", f"Sentiment: {sentiment_label} ({sentiment_score:+.2f})")
        yield _sse("sentiment", sentiment_result)

        try:
            geo_result = await geo_task
        except Exception:
            geo_result = {
                "policy_impact": "neutral",
                "impact_score": 0.0,
                "risk_factors": [],
                "regulatory_environment": "Unable to assess",
                "summary": "Geo-policy analysis could not be completed.",
            }
        policy_impact = geo_result.get("policy_impact", "neutral")
        yield _sse_stage("geo_policy", "complete", f"Policy impact: {policy_impact}")
        yield _sse("geo_policy", geo_result)
        await asyncio.sleep(0.1)

        # Stage 5: Volatility & Risk
        yield _sse_stage("volatility", "running", "Computing volatility and risk metrics...")
        volatility = compute_volatility_risk(price_history)
        risk_level = volatility.get("risk_level", "N/A")
        vol_regime = volatility.get("volatility_regime", "N/A")
        yield _sse_stage("volatility", "complete", f"Risk: {risk_level} | Volatility: {vol_regime}")
        yield _sse("volatility", volatility)
        await asyncio.sleep(0.1)

        # Stage 6: Outlook Aggregation
        yield _sse_stage("signal", "running", "Aggregating all analyses into market outlook...")
        try:
            signal_result = await aggregate_signal(
                ticker, company_name, market_data, technicals,
                sentiment_result, geo_result, volatility,
            )
        except Exception:
            signal_result = {
                "signal": "NEUTRAL",
                "confidence": 0.3,
                "reasoning": "Outlook aggregation could not be completed. Defaulting to neutral.",
                "bull_case": "Insufficient data for bull case analysis.",
                "bear_case": "Insufficient data for bear case analysis.",
                "key_factors": [],
                "risk_warning": "This is an AI-generated market insight for informational purposes only. It is not financial advice. Always conduct your own research and consult a qualified financial advisor before making investment decisions.",
            }
        final_signal = signal_result.get("signal", "NEUTRAL")
        confidence = signal_result.get("confidence", 0.5)
        yield _sse_stage("signal", "complete", f"Outlook: {final_signal} (confidence: {confidence:.0%})")
        yield _sse("signal", signal_result)

        # Save to database
        try:
            research = StockResearch(
                user_id=user.id,
                ticker=ticker,
                company_name=company_name,
                signal=final_signal,
                confidence=confidence,
                price_at_research=current_price,
                market_data={
                    "sector": market_data.get("sector"),
                    "market_cap": market_data.get("market_cap"),
                    "current_price": current_price,
                    "financials": market_data.get("financials"),
                    "dividends": market_data.get("dividends"),
                },
                technical_indicators=technicals,
                news_sentiment=sentiment_result,
                geo_policy=geo_result,
                volatility_risk=volatility,
                aggregated_signal=signal_result,
            )
            db.add(research)
            await db.commit()
            await db.refresh(research)
            research_id = research.id
        except Exception:
            research_id = None

        # Complete event
        yield _sse("complete", {
            "research_id": research_id,
            "ticker": ticker,
            "company_name": company_name,
            "signal": final_signal,
            "confidence": confidence,
            "current_price": current_price,
        })

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history")
@limiter.limit(READ_LIMIT)
async def research_history(
    request: Request,
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's stock research history."""
    result = await db.execute(
        select(StockResearch)
        .where(StockResearch.user_id == user.id)
        .order_by(StockResearch.created_at.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    return {
        "history": [
            {
                "id": r.id,
                "ticker": r.ticker,
                "company_name": r.company_name,
                "signal": r.signal,
                "confidence": r.confidence,
                "price_at_research": r.price_at_research,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ]
    }


@router.get("/research/{research_id}")
@limiter.limit(READ_LIMIT)
async def research_detail(
    request: Request,
    research_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full research detail by ID."""
    research = await db.get(StockResearch, research_id)
    if not research or research.user_id != user.id:
        raise HTTPException(404, "Research not found")
    return {
        "id": research.id,
        "ticker": research.ticker,
        "company_name": research.company_name,
        "signal": research.signal,
        "confidence": research.confidence,
        "price_at_research": research.price_at_research,
        "market_data": research.market_data,
        "technical_indicators": research.technical_indicators,
        "news_sentiment": research.news_sentiment,
        "geo_policy": research.geo_policy,
        "volatility_risk": research.volatility_risk,
        "aggregated_signal": research.aggregated_signal,
        "created_at": research.created_at.isoformat() if research.created_at else None,
    }


@router.post("/backtest")
@limiter.limit(ANALYSIS_LIMIT)
async def run_backtest(
    request: Request,
    body: dict = Body(...),
    user: User = Depends(get_current_user),
):
    """Run a simulated backtest for a ticker and signal."""
    ticker = (body.get("ticker") or "").upper().strip()
    signal = (body.get("signal") or "NEUTRAL").upper()
    lookback_days = body.get("lookback_days", 90)

    if not ticker:
        raise HTTPException(400, "Ticker is required")
    if signal not in ("BULLISH", "NEUTRAL", "BEARISH"):
        raise HTTPException(400, "Signal must be BULLISH, NEUTRAL, or BEARISH")

    from services.stock_data_service import fetch_market_data
    from services.technical_analysis import simulate_backtest

    market_data = await fetch_market_data(ticker, period="1y")
    price_history = market_data.get("price_history", [])

    if len(price_history) < 2:
        raise HTTPException(400, "Insufficient price data for backtest")

    result = simulate_backtest(price_history, signal, lookback_days)
    result["ticker"] = ticker
    result["company_name"] = market_data.get("company_name", ticker)
    return result
