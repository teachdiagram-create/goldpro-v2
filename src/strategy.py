import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════
#  STRATEGY 1: RANGE (RSI Double Top/Bottom)
# ══════════════════════════════════════════════════════════════
def detect_double_top_sell(
    rsi: pd.Series,
    lookback: int = 50,
    threshold: float = 70.0,
    max_bars_since_peak: int = 2,
    min_decline: float = 1.0,
):
    """تشخیص الگوی دابل تاپ در RSI برای سیگنال SELL"""
    r = rsi.tail(lookback).to_numpy()
    n = len(r)
    if n < 15:
        return None

    up_crosses = []
    for i in range(1, n):
        if r[i - 1] <= threshold < r[i]:
            up_crosses.append(i)

    if len(up_crosses) < 2:
        return None

    first_up = up_crosses[-2]
    second_up = up_crosses[-1]

    between = r[first_up:second_up]
    if len(between) == 0 or np.min(between) >= threshold:
        return None

    segment = r[second_up:]
    peak_offset = int(np.argmax(segment))
    peak_idx = second_up + peak_offset
    peak_value = float(segment[peak_offset])

    if peak_value < threshold:
        return None

    bars_since_peak = (n - 1) - peak_idx
    if bars_since_peak < 1 or bars_since_peak > max_bars_since_peak:
        return None

    current = float(r[-1])
    if current >= peak_value:
        return None

    if peak_value - current < min_decline:
        return None

    return {
        "pattern": "double_top",
        "strategy": "RANGE",
        "peak1_value": round(float(np.max(r[first_up:second_up])), 2),
        "peak2_value": round(peak_value, 2),
        "current_rsi": round(current, 2),
        "bars_since_peak": bars_since_peak,
    }


def detect_double_bottom_buy(
    rsi: pd.Series,
    lookback: int = 50,
    threshold: float = 30.0,
    max_bars_since_trough: int = 2,
    min_rise: float = 1.0,
):
    """تشخیص الگوی دابل باتم در RSI برای سیگنال BUY"""
    r = rsi.tail(lookback).to_numpy()
    n = len(r)
    if n < 15:
        return None

    down_crosses = []
    for i in range(1, n):
        if r[i - 1] >= threshold > r[i]:
            down_crosses.append(i)

    if len(down_crosses) < 2:
        return None

    first_down = down_crosses[-2]
    second_down = down_crosses[-1]

    between = r[first_down:second_down]
    if len(between) == 0 or np.max(between) <= threshold:
        return None

    segment = r[second_down:]
    trough_offset = int(np.argmin(segment))
    trough_idx = second_down + trough_offset
    trough_value = float(segment[trough_offset])

    if trough_value > threshold:
        return None

    bars_since_trough = (n - 1) - trough_idx
    if bars_since_trough < 1 or bars_since_trough > max_bars_since_trough:
        return None

    current = float(r[-1])
    if current <= trough_value:
        return None

    if current - trough_value < min_rise:
        return None

    return {
        "pattern": "double_bottom",
        "strategy": "RANGE",
        "trough1_value": round(float(np.min(r[first_down:second_down])), 2),
        "trough2_value": round(trough_value, 2),
        "current_rsi": round(current, 2),
        "bars_since_trough": bars_since_trough,
    }


# ══════════════════════════════════════════════════════════════
#  STRATEGY 2: TREND (EMA Cross + MACD)
# ══════════════════════════════════════════════════════════════
def detect_trend_signal(df: pd.DataFrame):
    """
    استراتژی روندی:
    - SELL: EMA_fast از بالا به پایین EMA_slow + MACD < Signal
    - BUY:  EMA_fast از پایین به بالا EMA_slow + MACD > Signal
    """
    if len(df) < 55:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # بررسی کراس EMA
    cross_up = (prev["ema_fast"] <= prev["ema_slow"]) and (last["ema_fast"] > last["ema_slow"])
    cross_down = (prev["ema_fast"] >= prev["ema_slow"]) and (last["ema_fast"] < last["ema_slow"])

    if not (cross_up or cross_down):
        return None

    # تأیید با MACD
    if cross_up and last["macd"] > last["macd_signal"]:
        return {
            "pattern": "trend_ema_cross",
            "strategy": "TREND",
            "direction": "BUY",
            "ema_fast": round(float(last["ema_fast"]), 2),
            "ema_slow": round(float(last["ema_slow"]), 2),
            "macd_hist": round(float(last["macd_hist"]), 2),
        }

    if cross_down and last["macd"] < last["macd_signal"]:
        return {
            "pattern": "trend_ema_cross",
            "strategy": "TREND",
            "direction": "SELL",
            "ema_fast": round(float(last["ema_fast"]), 2),
            "ema_slow": round(float(last["ema_slow"]), 2),
            "macd_hist": round(float(last["macd_hist"]), 2),
        }

    return None