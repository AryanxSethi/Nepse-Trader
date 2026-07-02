import math
import pandas as pd
import pandas_ta as ta


def _clean(val):
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def compute_indicators(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    closes = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    volumes = df["volume"].astype(float)

    rsi = ta.rsi(closes, length=14)
    macd_result = ta.macd(closes)
    bb = ta.bbands(closes, length=20)
    atr = ta.atr(highs, lows, closes, length=14)
    adx = ta.adx(highs, lows, closes, length=14)

    ema12 = ta.ema(closes, length=12)
    ema26 = ta.ema(closes, length=26)
    sma20 = ta.sma(closes, length=20)
    sma50 = ta.sma(closes, length=50)

    current = {
        "close": _clean(float(closes.iloc[-1])) if len(closes) else None,
        "rsi": _clean(float(rsi.iloc[-1])) if rsi is not None and not rsi.isna().all() else None,
        "macd": _clean(float(macd_result.iloc[-1, 0])) if macd_result is not None and len(macd_result) else None,
        "macd_signal": _clean(float(macd_result.iloc[-1, 1])) if macd_result is not None and len(macd_result) else None,
        "macd_hist": _clean(float(macd_result.iloc[-1, 2])) if macd_result is not None and len(macd_result) else None,
        "bb_upper": _clean(float(bb.iloc[-1, 0])) if bb is not None and len(bb) else None,
        "bb_middle": _clean(float(bb.iloc[-1, 1])) if bb is not None and len(bb) else None,
        "bb_lower": _clean(float(bb.iloc[-1, 2])) if bb is not None and len(bb) else None,
        "atr": _clean(float(atr.iloc[-1])) if atr is not None and not atr.isna().all() else None,
        "adx": _clean(float(adx.iloc[-1, 0])) if adx is not None and len(adx) else None,
        "ema12": _clean(float(ema12.iloc[-1])) if ema12 is not None and not ema12.isna().all() else None,
        "ema26": _clean(float(ema26.iloc[-1])) if ema26 is not None and not ema26.isna().all() else None,
        "sma20": _clean(float(sma20.iloc[-1])) if sma20 is not None and not sma20.isna().all() else None,
        "sma50": _clean(float(sma50.iloc[-1])) if sma50 is not None and not sma50.isna().all() else None,
    }

    trend = "neutral"
    if current["sma20"] and current["sma50"] and current["close"]:
        if current["sma20"] > current["sma50"] and current["close"] > current["sma20"]:
            trend = "uptrend"
        elif current["sma20"] < current["sma50"] and current["close"] < current["sma20"]:
            trend = "downtrend"

    current["trend"] = trend
    current["volume_avg"] = _clean(float(volumes.tail(20).mean())) if len(volumes) >= 20 else None
    current["volume_recent"] = _clean(float(volumes.tail(5).mean())) if len(volumes) >= 5 else None

    return current


def compute_signal(indicators: dict) -> tuple:
    score = 0
    reasons = []

    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi < 30:
            score += 2
            reasons.append("Oversold (RSI < 30)")
        elif rsi < 40:
            score += 1
            reasons.append("RSI approaching oversold")
        elif rsi > 70:
            score -= 2
            reasons.append("Overbought (RSI > 70)")
        elif rsi > 60:
            score -= 1
            reasons.append("RSI approaching overbought")

    macd = indicators.get("macd")
    macd_sig = indicators.get("macd_signal")
    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            score += 1
            reasons.append("MACD bullish crossover")
        else:
            score -= 1
            reasons.append("MACD bearish crossover")

    trend = indicators.get("trend", "neutral")
    if trend == "uptrend":
        score += 1
        reasons.append("Price in uptrend")
    elif trend == "downtrend":
        score -= 1
        reasons.append("Price in downtrend")

    vol_avg = indicators.get("volume_avg")
    vol_rec = indicators.get("volume_recent")
    if vol_avg and vol_rec:
        if vol_rec > vol_avg * 1.5:
            score += 1
            reasons.append("Above-average volume")
        elif vol_rec < vol_avg * 0.5:
            score -= 1
            reasons.append("Below-average volume")

    if score >= 2:
        return "BUY", min(95, 50 + score * 10), "; ".join(reasons)
    elif score <= -2:
        return "SELL", min(95, 50 + abs(score) * 10), "; ".join(reasons)
    else:
        return "HOLD", 50 + score * 5, "; ".join(reasons) if reasons else "No clear signal"
