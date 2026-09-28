import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════
#  SELL — Double Top در ناحیه Overbought (RSI > 70)
# ══════════════════════════════════════════════════════════════
def detect_double_top_sell(
    rsi: pd.Series,
    lookback: int = 50,
    threshold: float = 70.0,
    max_bars_since_peak: int = 2,
    min_decline: float = 1.0,
):
    """
    تشخیص الگوی دابل تاپ در RSI برای سیگنال SELL

    Parameters
    ----------
    rsi                    : سری RSI (فقط کندل‌های بسته‌شده)
    lookback               : تعداد کندل برای جستجو
    threshold              : سطح اشباع خرید (پیش‌فرض 70)
    max_bars_since_peak    : حداکثر فاصله فعلی از سقف دوم (پیش‌فرض 2)
    min_decline            : حداقل افت RSI از سقف (پیش‌فرض 1.0)
    """
    r = rsi.tail(lookback).to_numpy()
    n = len(r)
    if n < 15:
        return None

    # ── پیدا کردن کراس‌های بالا/پایین threshold ──
    up_crosses = []    # کراس به بالا (از زیر به بالای 70)
    for i in range(1, n):
        if r[i - 1] <= threshold < r[i]:
            up_crosses.append(i)

    if len(up_crosses) < 2:
        return None

    first_up = up_crosses[-2]   # اولین نفوذ
    second_up = up_crosses[-1]  # دومین نفوذ

    # ── بین دو نفوذ باید RSI به زیر 70 برگشته باشه ──
    between = r[first_up:second_up]
    if len(between) == 0 or np.min(between) >= threshold:
        return None

    # ── پیدا کردن سقف دوم (بیشترین RSI از second_up به بعد) ──
    segment = r[second_up:]
    peak_offset = int(np.argmax(segment))
    peak_idx = second_up + peak_offset
    peak_value = float(segment[peak_offset])

    # سقف دوم باید بالای threshold باشه
    if peak_value < threshold:
        return None

    # ── فاصله فعلی از سقف دوم ──
    bars_since_peak = (n - 1) - peak_idx

    # باید 1 یا 2 کندل از سقف گذشته باشه (نه بیشتر، نه صفر)
    if bars_since_peak < 1 or bars_since_peak > max_bars_since_peak:
        return None

    # ── مقدار فعلی باید پایین‌تر از سقف باشه (شروع نزول) ──
    current = float(r[-1])
    if current >= peak_value:
        return None

    # حداقل افت
    if peak_value - current < min_decline:
        return None

    return {
        "pattern": "double_top",
        "peak1_value": round(float(np.max(r[first_up:second_up])), 2),
        "peak2_value": round(peak_value, 2),
        "current_rsi": round(current, 2),
        "bars_since_peak": bars_since_peak,
    }


# ══════════════════════════════════════════════════════════════
#  BUY — Double Bottom در ناحیه Oversold (RSI < 30)
# ══════════════════════════════════════════════════════════════
def detect_double_bottom_buy(
    rsi: pd.Series,
    lookback: int = 50,
    threshold: float = 30.0,
    max_bars_since_trough: int = 2,
    min_rise: float = 1.0,
):
    """تشخیص دابل باتم در RSI برای BUY (متقارن با دابل تاپ)"""
    r = rsi.tail(lookback).to_numpy()
    n = len(r)
    if n < 15:
        return None

    down_crosses = []  # کراس به پایین
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

    # کف دوم (کمترین مقدار از second_down به بعد)
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
        "trough1_value": round(float(np.min(r[first_down:second_down])), 2),
        "trough2_value": round(trough_value, 2),
        "current_rsi": round(current, 2),
        "bars_since_trough": bars_since_trough,
    }