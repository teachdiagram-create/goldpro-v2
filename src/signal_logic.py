"""
Signal Logic - Interface between strategy and infrastructure.

این فایل ثابته. اگه استراتژی عوض شد، این فایل دست نمی‌خوره.

استراتژی فقط باید دو تا تابع از src/strategy.py بده:
    detect_double_top_sell(rsi_series) -> dict | None
    detect_double_bottom_buy(rsi_series) -> dict | None

خروجی strategy (کلیدها اختیاری‌ان - با .get امن خونده می‌شن):
    SELL: peak1_value, peak2_value, current_rsi
    BUY:  trough1_value, trough2_value, current_rsi
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


def _format_reason(setup: dict, side: str) -> str:
    """
    ساخت reason پویا از setup.
    اگه کلیدهای استاندارد نبودن، یه متن عمومی می‌سازه.
    """
    if side == "SELL":
        p1 = setup.get("peak1_value")
        p2 = setup.get("peak2_value")
        cur = setup.get("current_rsi")
        if p1 is not None and p2 is not None:
            reason = f"RSI double top: {p1} -> {p2}"
            if cur is not None:
                reason += f" (now {cur})"
            return reason

    elif side == "BUY":
        t1 = setup.get("trough1_value")
        t2 = setup.get("trough2_value")
        cur = setup.get("current_rsi")
        if t1 is not None and t2 is not None:
            reason = f"RSI double bottom: {t1} -> {t2}"
            if cur is not None:
                reason += f" (now {cur})"
            return reason

    # fallback
    return setup.get("reason", f"{side} signal")


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

    # ── پارامترهای پایه ──
    price = float(current["close"])
    atr_ = float(current["atr"])
    adx_ = float(current["adx"])
    rsi_ = float(current["rsi"])
    dt_str = str(current["datetime"])

    # ── فیلتر ساعت ممنوعه ──
    if _is_blocked_hour(dt_str):
        return None

    # ── دیکشنری پایه (مشترک بین BUY و SELL) ──
    base = {
        "timeframe": timeframe,
        "rsi": round(rsi_, 1),
        "adx": round(adx_, 1),
        "atr": round(atr_, 2),
        "time": dt_str,
    }

    # ══════════════════════════════════════════
    #  SELL: Double Top
    # ══════════════════════════════════════════
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
            "reason": _format_reason(sell_setup, "SELL"),
        }

    # ══════════════════════════════════════════
    #  BUY: Double Bottom
    # ══════════════════════════════════════════
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
            "reason": _format_reason(buy_setup, "BUY"),
        }

    return None