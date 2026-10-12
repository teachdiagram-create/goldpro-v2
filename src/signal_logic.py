from datetime import datetime, timezone

from src.config import (
    TP_ATR_MULT, SL_ATR_MULT,
    SL_STRUCTURE_BUFFER,
    ATR_MIN_USD, ATR_MAX_USD,
    MIN_SL_USD, MIN_TP_USD,
    BLOCKED_HOURS_UTC,
    compute_atr_effective, compute_sl_tp,
)
from src.strategy import detect_double_top_sell, detect_double_bottom_buy


def _is_blocked_hour(dt_str: str) -> bool:
    """چک کن ساعت UTC جزو ساعت‌های ممنوعه است یا نه."""
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.hour in BLOCKED_HOURS_UTC
    except Exception:
        return False


def evaluate_signal(df, timeframe: str = "5min"):
    """
    ارزیابی آخرین کندل بسته‌شده با استراتژی RSI Double Top/Bottom.
    SL ترکیبی (ساختار + ATR)، TP فقط ATR-based. R:R تضمین ≥ 1.5.
    """
    closed = df.iloc[:-1]
    current = closed.iloc[-1]

    rsi_series = closed["rsi"]

    price = float(current["close"])
    atr_raw = float(current["atr"])

    # ── ATR clamp ──
    atr_ = compute_atr_effective(atr_raw)
    if atr_ <= 0:
        return None  # بازار مرده، سیگنال نده

    # ── ساعت ممنوعه ──
    dt_str = str(current["datetime"])
    if _is_blocked_hour(dt_str):
        return None

    adx_ = float(current["adx"])
    rsi_ = float(current["rsi"])

    base = {
        "timeframe": timeframe,
        "rsi": round(rsi_, 1),
        "adx": round(adx_, 1),
        "atr": round(atr_, 2),
        "time": dt_str,
    }

    # ── SELL: Double Top ──
    sell_setup = detect_double_top_sell(rsi_series)
    if sell_setup:
        recent_high = float(closed["high"].tail(20).max())
        sl, tp, sl_dist, tp_dist, rr = compute_sl_tp(
            "SELL", price, atr_, recent_high=recent_high
        )
        if sl is None:
            return None

        return {
            **base,
            "side": "SELL",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "sl_distance": sl_dist,
            "tp_distance": tp_dist,
            "rr": rr,
            "reason": (
                f"RSI double top: {sell_setup['peak1_value']} → "
                f"{sell_setup['peak2_value']} (now {sell_setup['current_rsi']})"
            ),
        }

    # ── BUY: Double Bottom ──
    buy_setup = detect_double_bottom_buy(rsi_series)
    if buy_setup:
        recent_low = float(closed["low"].tail(20).min())
        sl, tp, sl_dist, tp_dist, rr = compute_sl_tp(
            "BUY", price, atr_, recent_low=recent_low
        )
        if sl is None:
            return None

        return {
            **base,
            "side": "BUY",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "sl_distance": sl_dist,
            "tp_distance": tp_dist,
            "rr": rr,
            "reason": (
                f"RSI double bottom: {buy_setup['trough1_value']} → "
                f"{buy_setup['trough2_value']} (now {buy_setup['current_rsi']})"
            ),
        }

    return None