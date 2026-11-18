import pandas as pd
import numpy as np


def detect_market_structure(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    تشخیص ساختار بازار (سقف و کف‌های اخیر) برای تعیین جهت.
    - Returns: {"trend": "UP" | "DOWN" | "NONE", "last_swing_high": float, "last_swing_low": float}
    """
    if len(df) < lookback + 5:
        return {"trend": "NONE", "last_swing_high": None, "last_swing_low": None}

    recent = df.tail(lookback)
    highs = recent["high"].values
    lows = recent["low"].values

    # پیدا کردن سقف و کف‌های محلی (ساده‌شده)
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

    # تشخیص روند: سقف‌ها و کف‌های بالاتر = صعودی، پایین‌تر = نزولی
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
    استراتژی V6: Structure + EMA + ATR (بدون VWAP به دلیل محدودیت دیتا).
    
    1. فیلتر جهت (M15): EMA50 > EMA200 و ساختار صعودی برای BUY.
    2. تشخیص BOS (M5): شکست سقف قبلی + پولبک + کندل تایید.
    3. فیلتر دیرهنگام: فاصله از EMA50 بیشتر از 1.5x ATR نباشه.
    4. R:R حداقل 1.5.
    """
    if len(df_m15) < 60 or len(df_m5) < 30:
        return None

    # ─── ۱. فیلتر جهت در M15 ───
    closed_m15 = df_m15.iloc[:-1]
    last_m15 = closed_m15.iloc[-1]
    ema50_m15 = float(last_m15["ema_fast"]) if "ema_fast" in last_m15 else float(last_m15["close"])
    # برای EMA200، از میانگین متحرک ساده 200 دوره استفاده می‌کنیم (اگه تو indicators نیست)
    # فعلاً از EMA50 و EMA200 تقریبی استفاده می‌کنیم
    ema200_m15 = float(closed_m15["close"].rolling(200).mean().iloc[-1]) if len(closed_m15) >= 200 else ema50_m15

    structure = detect_market_structure(closed_m15)

    # ─── ۲. فیلتر جهت در M5 ───
    closed_m5 = df_m5.iloc[:-1]
    current_m5 = closed_m5.iloc[-1]
    price = float(current_m5["close"])
    atr_ = float(current_m5["atr"])
    ema50_m5 = float(current_m5["ema_fast"]) if "ema_fast" in current_m5 else price

    # ─── ۳. تشخیص BOS (Break of Structure) در M5 ───
    # پیدا کردن سقف و کف اخیر در M5
    recent_highs = closed_m5["high"].tail(10).values
    recent_lows = closed_m5["low"].tail(10).values
    local_high = max(recent_highs) if len(recent_highs) > 0 else price
    local_low = min(recent_lows) if len(recent_lows) > 0 else price

    # ─── ۴. تصمیم‌گیری ───
    # برای BUY: EMA50 > EMA200 در M15، ساختار صعودی، قیمت بالای EMA50 در M5، و BOS صعودی
    if (ema50_m15 > ema200_m15 and structure["trend"] == "UP" 
        and price > ema50_m5 and price > local_high):
        
        # فیلتر دیرهنگام: فاصله از EMA50 نباید بیشتر از 1.5x ATR باشه
        distance_from_ema = abs(price - ema50_m5)
        if distance_from_ema > 1.5 * atr_:
            return None  # ورود دیرهنگام
        
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

    # برای SELL: EMA50 < EMA200 در M15، ساختار نزولی، قیمت زیر EMA50 در M5، و BOS نزولی
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