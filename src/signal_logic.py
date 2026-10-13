"""
Signal Logic - Interface between strategy and infrastructure.

این فایل ثابته. اگه استراتژی عوض شد، این فایل دست نمی‌خوره.
استراتژی فقط باید دو تا تابع از src/strategy.py بده:
    detect_double_top_sell(rsi_series) -> setup | None
    detect_double_bottom_buy(rsi_series) -> setup | None
"""
from datetime import datetime, timezone

from src.config import (
    BLOCKED_HOURS_UTC,
    compute_sl_tp,
)
from src.strategy import detect_double_top_sell, detect_double_bottom_buy


def _is_blocked_hour(dt_str: str) -> bool:
    """چک کن ساعت UTC ممنوعه هست یا نه."""
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.hour in BLOCKED_HOURS_UTC
    except Exception:
        return False


def evaluate_signal(df, timeframe: str = "5min"):
    """
    ارزیابی آخرین کندل بسته‌شده.

    اینترفیس خروجی (dict) - ثابت:
        {
            "timeframe": str,
            "side": "BUY" | "SELL",
            "entry": float,
            "sl": float,
            "tp": float,
            "sl_distance": float,
            "tp_distance": float,
            "rr": float,
            "rsi": float,
            "adx": float,
            "atr": float,
            "time": str,
            "reason": str,
        }

    یا None اگه سیگنالی نباشه.
    """
    closed = df.iloc[:-1]
    current = closed.iloc[-1]
    rsi_series = closed["rsi"]

    price = float(current["close"])
    atr_ = float(current["atr"])
    adx_ = float(current["adx"])
    rsi_ = float(current["rsi"])
    dt_str = str(current["datetime"])

    # ── فیلتر ساعت ممنوعه ──
    if _is_blocked_hour(dt_str):
        return None

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
        sl, tp, sd, td, rr = compute_sl_tp("SELL", price, atr_)
        if sl is None:
            return None

        return {
            **base,
            "side": "SELL",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "sl_distance": sd,
            "tp_distance": td,
            "rr": rr,
            "reason": (
                f"RSI double top: {sell_setup['peak1_value']} → "
                f"{sell_setup['peak2_value']} (now {sell_setup['current_rsi']})"
            ),
        }

    # ── BUY: Double Bottom ──
    buy_setup = detect_double_bottom_buy(rsi_series)
    if buy_setup:
        sl, tp, sd, td, rr = compute_sl_tp("BUY", price, atr_)
        if sl is None:
            return None

        return {
            **base,
            "side": "BUY",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "sl_distance": sd,
            "tp_distance": td,
            "rr": rr,
            "reason": (
                f"RSI double bottom: {buy_setup['trough1_value']} → "
                f"{buy_setup['trough2_value']} (now {buy_setup['current_rsi']})"
            ),
        }

    return None