"""Stock data service: yfinance for market data + optional Alpha Vantage for news sentiment."""
import os
import asyncio
from datetime import datetime


async def search_ticker(query: str) -> list[dict]:
    """Search for stock tickers by name or symbol using yfinance."""
    import yfinance as yf

    def _search():
        results = []
        # Try direct ticker lookup first
        try:
            ticker = yf.Ticker(query.upper())
            info = ticker.info or {}
            if info.get("symbol"):
                results.append({
                    "symbol": info["symbol"],
                    "name": info.get("longName") or info.get("shortName") or query.upper(),
                    "exchange": info.get("exchange", ""),
                    "type": info.get("quoteType", "EQUITY"),
                })
        except Exception:
            pass

        # Also try search
        try:
            search_results = yf.Search(query)
            for item in getattr(search_results, "quotes", [])[:10]:
                symbol = item.get("symbol", "")
                if symbol and not any(r["symbol"] == symbol for r in results):
                    results.append({
                        "symbol": symbol,
                        "name": item.get("longname") or item.get("shortname") or symbol,
                        "exchange": item.get("exchange", ""),
                        "type": item.get("quoteType", "EQUITY"),
                    })
        except Exception:
            pass

        return results[:10]

    return await asyncio.to_thread(_search)


async def fetch_market_data(ticker: str, period: str = "6mo") -> dict:
    """Fetch comprehensive market data for a ticker."""
    import yfinance as yf

    def _fetch():
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period=period)

        # Build price history
        price_history = []
        for date, row in hist.iterrows():
            price_history.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        # Financials summary
        financials = {}
        try:
            financials = {
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "eps": info.get("trailingEps"),
                "revenue": info.get("totalRevenue"),
                "profit_margin": info.get("profitMargins"),
                "debt_to_equity": info.get("debtToEquity"),
                "return_on_equity": info.get("returnOnEquity"),
                "free_cash_flow": info.get("freeCashflow"),
                "beta": info.get("beta"),
            }
        except Exception:
            pass

        # Dividends
        dividends = {}
        try:
            dividends = {
                "dividend_yield": info.get("dividendYield"),
                "dividend_rate": info.get("dividendRate"),
                "payout_ratio": info.get("payoutRatio"),
                "ex_dividend_date": info.get("exDividendDate"),
            }
        except Exception:
            pass

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not current_price and price_history:
            current_price = price_history[-1]["close"]

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("longName") or info.get("shortName") or ticker.upper(),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap"),
            "current_price": current_price,
            "currency": info.get("currency", "USD"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "price_history": price_history,
            "financials": financials,
            "dividends": dividends,
        }

    return await asyncio.to_thread(_fetch)


async def fetch_news(ticker: str) -> list[dict]:
    """Fetch news for a ticker from yfinance + optional Alpha Vantage."""
    import yfinance as yf

    def _fetch_yf_news():
        t = yf.Ticker(ticker)
        news_items = []
        try:
            raw_news = t.news or []
            for item in raw_news[:15]:
                content = item.get("content", {}) if isinstance(item, dict) else {}
                # Handle both old and new yfinance news format
                title = item.get("title") or content.get("title", "")
                publisher = item.get("publisher") or content.get("provider", {}).get("displayName", "")
                link = item.get("link") or content.get("canonicalUrl", {}).get("url", "")
                pub_date = item.get("providerPublishTime")
                if pub_date and isinstance(pub_date, (int, float)):
                    pub_date = datetime.fromtimestamp(pub_date).isoformat()
                elif not pub_date:
                    pub_date = content.get("pubDate", "")

                if title:
                    news_items.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                        "published": pub_date,
                        "source": "yfinance",
                    })
        except Exception:
            pass
        return news_items

    news = await asyncio.to_thread(_fetch_yf_news)

    # Optional: Alpha Vantage news sentiment
    av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if av_key:
        try:
            import httpx
            url = (
                f"https://www.alphavantage.co/query"
                f"?function=NEWS_SENTIMENT&tickers={ticker}"
                f"&limit=10&apikey={av_key}"
            )
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                data = resp.json()
                for item in data.get("feed", [])[:10]:
                    # Find ticker-specific sentiment
                    ticker_sentiment = None
                    for ts in item.get("ticker_sentiment", []):
                        if ts.get("ticker") == ticker.upper():
                            ticker_sentiment = ts
                            break

                    news.append({
                        "title": item.get("title", ""),
                        "publisher": item.get("source", ""),
                        "link": item.get("url", ""),
                        "published": item.get("time_published", ""),
                        "source": "alpha_vantage",
                        "sentiment_score": float(ticker_sentiment["ticker_sentiment_score"]) if ticker_sentiment else None,
                        "sentiment_label": ticker_sentiment.get("ticker_sentiment_label") if ticker_sentiment else None,
                    })
        except Exception:
            pass

    return news
