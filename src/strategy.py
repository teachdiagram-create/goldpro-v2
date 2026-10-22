def detect_double_top_sell(rsi_series, lookback=50, threshold=70.0,
                          max_bars_since_peak=2, min_decline=1.0):
    """
    Returns:
        dict با کلیدهای peak1_value, peak2_value, current_rsi, bars_since_peak
        یا None اگه الگو نباشه
    """
    ...

def detect_double_bottom_buy(rsi_series, lookback=50, threshold=30.0,
                            max_bars_since_trough=2, min_rise=1.0):
    """
    Returns:
        dict با کلیدهای trough1_value, trough2_value, current_rsi, bars_since_trough
        یا None
    """
# ══════════════════════════════════════════════════════════════
#  TREND STRATEGY — EMA Cross + MACD Confirmation
# ══════════════════════════════════════════════════════════════
def detect_trend_signal(df, ema_fast=20, ema_slow=50):
    """
    استراتژی روندی: کراس EMA + تأیید MACD
    - SELL: EMA_fast از بالا به پایین EMA_slow + MACD < Signal
    - BUY:  EMA_fast از پایین به بالا EMA_slow + MACD > Signal
    """
    if len(df) < ema_slow + 5:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # کراس EMA
    cross_up = (prev["ema_fast"] <= prev["ema_slow"]) and (last["ema_fast"] > last["ema_slow"])
    cross_down = (prev["ema_fast"] >= prev["ema_slow"]) and (last["ema_fast"] < last["ema_slow"])

    if not (cross_up or cross_down):
        return None

    # تأیید MACD
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
    ...