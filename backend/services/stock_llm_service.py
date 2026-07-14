"""Stock LLM service: sentiment analysis, geo-policy assessment, and signal aggregation via local LLM."""
import json
import asyncio
from services.llm_service import _client, _build_system_message, _build_user_message, _call_chat
from prompts.stock_analysis_prompt import SENTIMENT_PROMPT, GEO_POLICY_PROMPT, SIGNAL_AGGREGATION_PROMPT


async def analyze_news_sentiment(ticker: str, company_name: str, news_items: list[dict]) -> dict:
    """Analyze news sentiment using local LLM."""
    if not news_items:
        return {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.0,
            "key_themes": ["No recent news available"],
            "articles": [],
            "summary": f"No recent news articles found for {company_name} ({ticker}). Sentiment is neutral by default.",
        }

    data = {
        "ticker": ticker,
        "company_name": company_name,
        "news_items": [
            {"title": n.get("title", ""), "publisher": n.get("publisher", ""), "published": n.get("published", ""), "source": n.get("source", "")}
            for n in news_items[:15]
        ],
    }

    def _call():
        sys = _build_system_message(SENTIMENT_PROMPT)
        user = _build_user_message(SENTIMENT_PROMPT, data)
        raw = _call_chat(sys, user, SENTIMENT_PROMPT.get("settingsJson"))
        return json.loads(raw) if isinstance(raw, str) else raw

    return await asyncio.to_thread(_call)


async def analyze_geo_policy(ticker: str, company_name: str, sector: str, news_items: list[dict]) -> dict:
    """Analyze geopolitical and regulatory risks using local LLM."""
    data = {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "news_items": [
            {"title": n.get("title", ""), "publisher": n.get("publisher", ""), "published": n.get("published", "")}
            for n in news_items[:15]
        ],
    }

    def _call():
        sys = _build_system_message(GEO_POLICY_PROMPT)
        user = _build_user_message(GEO_POLICY_PROMPT, data)
        raw = _call_chat(sys, user, GEO_POLICY_PROMPT.get("settingsJson"))
        return json.loads(raw) if isinstance(raw, str) else raw

    return await asyncio.to_thread(_call)


async def aggregate_signal(
    ticker: str,
    company_name: str,
    market_data: dict,
    technical_indicators: dict,
    news_sentiment: dict,
    geo_policy: dict,
    volatility_risk: dict,
) -> dict:
    """Aggregate all analyses into a market outlook using local LLM."""
    data = {
        "ticker": ticker,
        "company_name": company_name,
        "market_data": {
            "current_price": market_data.get("current_price"),
            "market_cap": market_data.get("market_cap"),
            "sector": market_data.get("sector"),
            "pe_ratio": (market_data.get("financials") or {}).get("pe_ratio"),
            "eps": (market_data.get("financials") or {}).get("eps"),
            "beta": (market_data.get("financials") or {}).get("beta"),
            "dividend_yield": (market_data.get("dividends") or {}).get("dividend_yield"),
            "52w_high": market_data.get("fifty_two_week_high"),
            "52w_low": market_data.get("fifty_two_week_low"),
        },
        "technical_indicators": {
            "rsi_14": technical_indicators.get("rsi_14"),
            "trend_summary": technical_indicators.get("trend_summary"),
            "sma_crossover": technical_indicators.get("sma_crossover"),
            "macd": technical_indicators.get("macd"),
            "bollinger_position": (technical_indicators.get("bollinger_bands") or {}).get("position"),
            "signals": technical_indicators.get("signals"),
        },
        "news_sentiment": {
            "overall_sentiment": news_sentiment.get("overall_sentiment"),
            "sentiment_score": news_sentiment.get("sentiment_score"),
            "key_themes": news_sentiment.get("key_themes"),
            "summary": news_sentiment.get("summary"),
        },
        "geo_policy": {
            "policy_impact": geo_policy.get("policy_impact"),
            "impact_score": geo_policy.get("impact_score"),
            "risk_factors": geo_policy.get("risk_factors"),
            "summary": geo_policy.get("summary"),
        },
        "volatility_risk": {
            "annualized_volatility": volatility_risk.get("annualized_volatility"),
            "max_drawdown": volatility_risk.get("max_drawdown"),
            "sharpe_ratio": volatility_risk.get("sharpe_ratio"),
            "risk_level": volatility_risk.get("risk_level"),
            "volatility_regime": volatility_risk.get("volatility_regime"),
            "risk_factors": volatility_risk.get("risk_factors"),
        },
    }

    def _call():
        sys = _build_system_message(SIGNAL_AGGREGATION_PROMPT)
        user = _build_user_message(SIGNAL_AGGREGATION_PROMPT, data)
        raw = _call_chat(sys, user, SIGNAL_AGGREGATION_PROMPT.get("settingsJson"))
        return json.loads(raw) if isinstance(raw, str) else raw

    return await asyncio.to_thread(_call)
