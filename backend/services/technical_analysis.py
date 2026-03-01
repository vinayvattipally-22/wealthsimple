"""Technical analysis service: indicators, volatility metrics, and backtesting."""
import math
from datetime import datetime


def compute_indicators(price_history: list[dict]) -> dict:
    """Compute technical indicators from price history using ta library."""
    import pandas as pd
    import numpy as np
    import ta

    if len(price_history) < 20:
        return {"error": "Insufficient price data", "data_points": len(price_history)}

    df = pd.DataFrame(price_history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Moving averages
    sma_20 = ta.trend.sma_indicator(close, window=20)
    sma_50 = ta.trend.sma_indicator(close, window=50)
    sma_200 = ta.trend.sma_indicator(close, window=200)
    ema_12 = ta.trend.ema_indicator(close, window=12)
    ema_26 = ta.trend.ema_indicator(close, window=26)

    # RSI
    rsi = ta.momentum.rsi(close, window=14)

    # MACD
    macd_line = ta.trend.macd(close)
    macd_signal = ta.trend.macd_signal(close)
    macd_hist = ta.trend.macd_diff(close)

    # Bollinger Bands
    bb_high = ta.volatility.bollinger_hband(close)
    bb_low = ta.volatility.bollinger_lband(close)
    bb_mid = ta.volatility.bollinger_mavg(close)

    # Volume metrics
    vol_sma = ta.trend.sma_indicator(volume.astype(float), window=20)

    latest = len(df) - 1
    current_price = float(close.iloc[latest])

    # SMA Crossover analysis
    sma_crossover = "neutral"
    if not pd.isna(sma_50.iloc[latest]) and not pd.isna(sma_200.iloc[latest]):
        if sma_50.iloc[latest] > sma_200.iloc[latest]:
            sma_crossover = "golden_cross"
        else:
            sma_crossover = "death_cross"

    # Trend summary
    trend_signals = []
    rsi_val = float(rsi.iloc[latest]) if not pd.isna(rsi.iloc[latest]) else 50
    if rsi_val > 70:
        trend_signals.append("overbought")
    elif rsi_val < 30:
        trend_signals.append("oversold")

    if not pd.isna(sma_20.iloc[latest]):
        if current_price > float(sma_20.iloc[latest]):
            trend_signals.append("above_sma20")
        else:
            trend_signals.append("below_sma20")

    if not pd.isna(macd_hist.iloc[latest]):
        if float(macd_hist.iloc[latest]) > 0:
            trend_signals.append("macd_bullish")
        else:
            trend_signals.append("macd_bearish")

    # Bollinger Band position
    bb_position = "middle"
    if not pd.isna(bb_high.iloc[latest]) and not pd.isna(bb_low.iloc[latest]):
        bb_range = float(bb_high.iloc[latest]) - float(bb_low.iloc[latest])
        if bb_range > 0:
            bb_pct = (current_price - float(bb_low.iloc[latest])) / bb_range
            if bb_pct > 0.8:
                bb_position = "upper"
            elif bb_pct < 0.2:
                bb_position = "lower"

    # Determine overall trend
    bullish_count = sum(1 for s in trend_signals if s in ["oversold", "above_sma20", "macd_bullish", "golden_cross"])
    bearish_count = sum(1 for s in trend_signals if s in ["overbought", "below_sma20", "macd_bearish", "death_cross"])
    if bullish_count > bearish_count:
        trend_summary = "bullish"
    elif bearish_count > bullish_count:
        trend_summary = "bearish"
    else:
        trend_summary = "neutral"

    # Build indicator history (last 30 days)
    indicator_history = []
    for i in range(max(0, latest - 29), latest + 1):
        entry = {"date": df["date"].iloc[i].strftime("%Y-%m-%d")}
        entry["close"] = float(close.iloc[i])
        if not pd.isna(sma_20.iloc[i]):
            entry["sma_20"] = round(float(sma_20.iloc[i]), 2)
        if not pd.isna(sma_50.iloc[i]):
            entry["sma_50"] = round(float(sma_50.iloc[i]), 2)
        if not pd.isna(bb_high.iloc[i]):
            entry["bb_upper"] = round(float(bb_high.iloc[i]), 2)
        if not pd.isna(bb_low.iloc[i]):
            entry["bb_lower"] = round(float(bb_low.iloc[i]), 2)
        if not pd.isna(rsi.iloc[i]):
            entry["rsi"] = round(float(rsi.iloc[i]), 2)
        indicator_history.append(entry)

    def _safe(series, idx):
        v = series.iloc[idx]
        return round(float(v), 2) if not pd.isna(v) else None

    return {
        "current_price": current_price,
        "sma_20": _safe(sma_20, latest),
        "sma_50": _safe(sma_50, latest),
        "sma_200": _safe(sma_200, latest),
        "ema_12": _safe(ema_12, latest),
        "ema_26": _safe(ema_26, latest),
        "rsi_14": round(rsi_val, 2),
        "macd": {
            "line": _safe(macd_line, latest),
            "signal": _safe(macd_signal, latest),
            "histogram": _safe(macd_hist, latest),
        },
        "bollinger_bands": {
            "upper": _safe(bb_high, latest),
            "middle": _safe(bb_mid, latest),
            "lower": _safe(bb_low, latest),
            "position": bb_position,
        },
        "volume_metrics": {
            "current_volume": int(volume.iloc[latest]),
            "avg_volume_20": int(float(vol_sma.iloc[latest])) if not pd.isna(vol_sma.iloc[latest]) else None,
            "volume_ratio": round(float(volume.iloc[latest]) / float(vol_sma.iloc[latest]), 2) if not pd.isna(vol_sma.iloc[latest]) and float(vol_sma.iloc[latest]) > 0 else None,
        },
        "trend_summary": trend_summary,
        "sma_crossover": sma_crossover,
        "signals": trend_signals,
        "indicator_history": indicator_history,
    }


def compute_volatility_risk(price_history: list[dict]) -> dict:
    """Compute volatility metrics and risk assessment."""
    import numpy as np

    if len(price_history) < 20:
        return {"error": "Insufficient price data", "data_points": len(price_history)}

    closes = [p["close"] for p in price_history]
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] != 0]

    if not returns:
        return {"error": "Cannot compute returns"}

    returns_arr = np.array(returns)

    # Daily and annualized volatility
    daily_vol = float(np.std(returns_arr))
    annual_vol = daily_vol * math.sqrt(252)

    # Max drawdown
    peak = closes[0]
    max_dd = 0
    for price in closes:
        if price > peak:
            peak = price
        dd = (peak - price) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (assuming risk-free rate of 4.5%)
    risk_free_daily = 0.045 / 252
    mean_return = float(np.mean(returns_arr))
    sharpe = (mean_return - risk_free_daily) / daily_vol if daily_vol > 0 else 0
    sharpe_annual = sharpe * math.sqrt(252)

    # VaR 95%
    var_95 = float(np.percentile(returns_arr, 5))

    # Volatility regime
    if annual_vol < 0.15:
        vol_regime = "low"
    elif annual_vol < 0.30:
        vol_regime = "moderate"
    elif annual_vol < 0.50:
        vol_regime = "high"
    else:
        vol_regime = "extreme"

    # Risk level
    risk_score = 0
    if annual_vol > 0.30:
        risk_score += 2
    elif annual_vol > 0.20:
        risk_score += 1
    if max_dd > 0.20:
        risk_score += 2
    elif max_dd > 0.10:
        risk_score += 1
    if sharpe_annual < 0:
        risk_score += 1

    if risk_score >= 4:
        risk_level = "HIGH"
    elif risk_score >= 2:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    # Risk factors
    risk_factors = []
    if annual_vol > 0.30:
        risk_factors.append(f"High annualized volatility ({annual_vol:.1%})")
    if max_dd > 0.15:
        risk_factors.append(f"Significant max drawdown ({max_dd:.1%})")
    if sharpe_annual < 0:
        risk_factors.append("Negative risk-adjusted returns")
    if var_95 < -0.03:
        risk_factors.append(f"Daily VaR 95% is {var_95:.2%}")
    if not risk_factors:
        risk_factors.append("Risk metrics within normal range")

    return {
        "daily_volatility": round(daily_vol, 6),
        "annualized_volatility": round(annual_vol, 4),
        "max_drawdown": round(max_dd, 4),
        "sharpe_ratio": round(sharpe_annual, 2),
        "var_95": round(var_95, 4),
        "volatility_regime": vol_regime,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
    }


def simulate_backtest(price_history: list[dict], signal: str, lookback_days: int = 90) -> dict:
    """Simulate a simple backtest: what if you followed the signal N days ago."""
    if len(price_history) < 2:
        return {"error": "Insufficient data for backtest"}

    # Use the data we have, up to lookback_days
    window = price_history[-min(lookback_days, len(price_history)):]
    entry_price = window[0]["close"]
    current_price = window[-1]["close"]
    entry_date = window[0]["date"]

    highs = [p["high"] for p in window]
    lows = [p["low"] for p in window]

    max_price = max(highs)
    min_price = min(lows)

    if signal == "BULLISH":
        return_pct = (current_price - entry_price) / entry_price if entry_price else 0
        max_gain_pct = (max_price - entry_price) / entry_price if entry_price else 0
        max_loss_pct = (min_price - entry_price) / entry_price if entry_price else 0
    elif signal == "BEARISH":
        return_pct = (entry_price - current_price) / entry_price if entry_price else 0
        max_gain_pct = (entry_price - min_price) / entry_price if entry_price else 0
        max_loss_pct = (entry_price - max_price) / entry_price if entry_price else 0
    else:
        return_pct = 0
        max_gain_pct = (max_price - entry_price) / entry_price if entry_price else 0
        max_loss_pct = (min_price - entry_price) / entry_price if entry_price else 0

    return {
        "signal": signal,
        "lookback_days": len(window),
        "entry_date": entry_date,
        "entry_price": round(entry_price, 2),
        "current_price": round(current_price, 2),
        "return_pct": round(return_pct, 4),
        "max_gain_pct": round(max_gain_pct, 4),
        "max_loss_pct": round(max_loss_pct, 4),
    }
