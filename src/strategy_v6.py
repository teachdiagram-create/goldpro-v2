import pandas as pd
import numpy as np


def detect_market_structure(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    تشخیص ساختار بازار (سقف و کف‌های اخیر) برای تعیین جهت.
    """
    if len(df) < lookback + 5:
        return {"trend": "NONE", "last_swing_high": None, "last_swing_low": None}

    recent = df.tail(lookback)
    highs = recent["high"].values
    lows = recent["low"].values

    swing_highs = []
    swing_lows = []
    for i in range(1, len(highs) - 1):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            swing_highs.append((i, highs[i]))
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            swing_lows.append((i, lows[i]))

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {"trend": "NONE", "last_swing_high": None, "last_swing_low": None}

    last_high = swing_highs[-1][1]
    prev_high = swing_highs[-2][1]
    last_low = swing_lows[-1][1]
    prev_low = swing_lows[-2][1]

    if last_high > prev_high and last_low > prev_low:
        trend = "UP"
    elif last_high < prev_high and last_low < prev_low:
        trend = "DOWN"
    else:
        trend = "NONE"

    return {
        "trend": trend,
        "last_swing_high": round(last_high, 2),
        "last_swing_low": round(last_low, 2),
        "prev_swing_high": round(prev_high, 2),
        "prev_swing_low": round(prev_low, 2),
    }


def detect_v6_signal(df_m5: pd.DataFrame, df_m15: pd.DataFrame) -> dict:
    """
    استراتژی V6: Structure + EMA + ATR.
    """
    if len(df_m15) < 60 or len(df_m5) < 30:
        return None

    # ─── ۱. فیلتر جهت در M15 ───
    closed_m15 = df_m15.iloc[:-1]
    last_m15 = closed_m15.iloc[-1]
    ema50_m15 = float(last_m15["ema_fast"]) if "ema_fast" in last_m15 else float(last_m15["close"])
    ema200_m15 = float(closed_m15["close"].rolling(200).mean().iloc[-1]) if len(closed_m15) >= 200 else ema50_m15

    structure = detect_market_structure(closed_m15)

    # ─── ۲. فیلتر جهت در M5 ───
    closed_m5 = df_m5.iloc[:-1]
    current_m5 = closed_m5.iloc[-1]
    price = float(current_m5["close"])
    atr_ = float(current_m5["atr"])
    ema50_m5 = float(current_m5["ema_fast"]) if "ema_fast" in current_m5 else price

    # ─── ۳. تشخیص BOS (Break of Structure) در M5 ───
    recent_highs = closed_m5["high"].tail(10).values
    recent_lows = closed_m5["low"].tail(10).values
    local_high = max(recent_highs) if len(recent_highs) > 0 else price
    local_low = min(recent_lows) if len(recent_lows) > 0 else price

    # ─── ۴. تصمیم‌گیری ───
    if (ema50_m15 > ema200_m15 and structure["trend"] == "UP" 
        and price > ema50_m5 and price > local_high):
        
        distance_from_ema = abs(price - ema50_m5)
        if distance_from_ema > 1.5 * atr_:
            return None
        
        return {
            "pattern": "v6_structure_buy",
            "strategy": "V6_STRUCTURE",
            "direction": "BUY",
            "ema50_m15": round(ema50_m15, 2),
            "ema200_m15": round(ema200_m15, 2),
            "structure_trend": structure["trend"],
            "local_high": round(local_high, 2),
            "local_low": round(local_low, 2),
        }

    if (ema50_m15 < ema200_m15 and structure["trend"] == "DOWN" 
        and price < ema50_m5 and price < local_low):
        
        distance_from_ema = abs(price - ema50_m5)
        if distance_from_ema > 1.5 * atr_:
            return None
        
        return {
            "pattern": "v6_structure_sell",
            "strategy": "V6_STRUCTURE",
            "direction": "SELL",
            "ema50_m15": round(ema50_m15, 2),
            "ema200_m15": round(ema200_m15, 2),
            "structure_trend": structure["trend"],
            "local_high": round(local_high, 2),
            "local_low": round(local_low, 2),
        }

    return None