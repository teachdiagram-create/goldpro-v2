"""
Signal Logic - Pure pattern detection + quality scoring.

فلسفه:
- الگوی دابل تاپ/باتم تنها تولیدکننده‌ی سیگنال است.
- فیلترها هیچ سیگنالی را رد نمی‌کنند.
- فیلترها فقط به هر سیگنال «وزن» (quality score) می‌دهند.

Interface (ثابت):
    evaluate_signal(df, timeframe) -> dict | None
"""
from src.config import compute_sl_tp
from src.strategy import detect_double_top_sell, detect_double_bottom_buy


def _compute_quality(adx_val: float, atr_val: float,
                     rsi_val: float, side: str) -> dict:
    """
    محاسبه‌ی وزن سیگنال بر اساس کیفیت.

    Returns:
        {
            "score": 0-100,
            "grade": "A" | "B" | "C" | "D",
            "flags": [...],
            "warnings": [...],
        }
    """
    score = 50  # پایه
    flags = []
    warnings = []

    # ── ADX (قدرت روند) ──
    if adx_val is None:
        warnings.append("ADX نامشخص")
    elif adx_val >= 50:
        score += 30
        flags.append("ADX قوی")
    elif adx_val >= 35:
        score += 20
        flags.append("ADX خوب")
    elif adx_val >= 25:
        score += 10
    elif adx_val >= 15:
        score -= 5
        warnings.append("ADX ضعیف")
    else:
        score -= 20
        warnings.append("ADX خیلی ضعیف - روند نیست")

    # ── ATR (نوسان) ──
    if atr_val is None:
        warnings.append("ATR نامشخص")
    elif atr_val < 0.5:
        score -= 25
        warnings.append("ATR خیلی کم - بازار مرده")
    elif atr_val < 1.0:
        score -= 10
        warnings.append("ATR کم")
    elif atr_val <= 4.0:
        score += 10
        flags.append("ATR مناسب")
    elif atr_val <= 6.0:
        score -= 5
        warnings.append("ATR بالا")
    else:
        score -= 15
        warnings.append("ATR خیلی بالا - نوسان خطرناک")

    # ── RSI (تأیید الگو) ──
    if rsi_val is not None:
        if side == "SELL":
            # دابل تاپ: RSI باید از سقف افتاده باشه
            if rsi_val <= 65:
                score += 10
                flags.append("RSI تأیید می‌کند")
            elif rsi_val >= 70:
                score -= 10
                warnings.append("RSI هنوز بالا - شاید زود باشه")
        elif side == "BUY":
            if rsi_val >= 35:
                score += 10
                flags.append("RSI تأیید می‌کند")
            elif rsi_val <= 30:
                score -= 10
                warnings.append("RSI هنوز پایین - شاید زود باشه")

    # ── محدود کردن ──
    score = max(0, min(100, score))

    # ── تعیین گرید ──
    if score >= 80:
        grade = "A"
    elif score >= 65:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "D"

    return {
        "score": score,
        "grade": grade,
        "flags": flags,
        "warnings": warnings,
    }


def _build_reason(setup: dict, side: str) -> str:
    """ساخت reason پویا از setup."""
    if side == "SELL":
        p1 = setup.get("peak1_value")
        p2 = setup.get("peak2_value")
        cur = setup.get("current_rsi")
        if p1 is not None and p2 is not None:
            r = f"RSI double top: {p1} -> {p2}"
            if cur is not None:
                r += f" (now {cur})"
            return r
    elif side == "BUY":
        t1 = setup.get("trough1_value")
        t2 = setup.get("trough2_value")
        cur = setup.get("current_rsi")
        if t1 is not None and t2 is not None:
            r = f"RSI double bottom: {t1} -> {t2}"
            if cur is not None:
                r += f" (now {cur})"
            return r
    return setup.get("reason", f"{side} signal")


def evaluate_signal(df, timeframe: str = "5min"):
    """
    ارزیابی آخرین کندل بسته‌شده.

    هیچ فیلتری سیگنال را رد نمی‌کند.
    فیلترها فقط به quality_score تبدیل می‌شوند.

    Returns:
        dict یا None (اگر الگویی نباشد)
    """
    closed = df.iloc[:-1]
    current = closed.iloc[-1]
    rsi_series = closed["rsi"]

    price = float(current["close"])
    atr_ = float(current["atr"])
    adx_ = float(current["adx"])
    rsi_ = float(current["rsi"])
    dt_str = str(current["datetime"])

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
            # SL/TP نشد - ولی سیگنال رو با sl/tp خالی بفرست
            return {
                **base,
                "side": "SELL",
                "entry": round(price, 2),
                "sl": None,
                "tp": None,
                "sl_distance": None,
                "tp_distance": None,
                "rr": None,
                "quality": _compute_quality(adx_, atr_, rsi_, "SELL"),
                "reason": _build_reason(sell_setup, "SELL"),
                "valid": False,
            }

        quality = _compute_quality(adx_, atr_, rsi_, "SELL")

        return {
            **base,
            "side": "SELL",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "sl_distance": sd,
            "tp_distance": td,
            "rr": rr,
            "quality": quality,
            "reason": _build_reason(sell_setup, "SELL"),
            "valid": True,
        }

    # ══════════════════════════════════════════
    #  BUY: Double Bottom
    # ══════════════════════════════════════════
    buy_setup = detect_double_bottom_buy(rsi_series)
    if buy_setup:
        sl, tp, sd, td, rr = compute_sl_tp("BUY", price, atr_)
        if sl is None:
            return {
                **base,
                "side": "BUY",
                "entry": round(price, 2),
                "sl": None,
                "tp": None,
                "sl_distance": None,
                "tp_distance": None,
                "rr": None,
                "quality": _compute_quality(adx_, atr_, rsi_, "BUY"),
                "reason": _build_reason(buy_setup, "BUY"),
                "valid": False,
            }

        quality = _compute_quality(adx_, atr_, rsi_, "BUY")

        return {
            **base,
            "side": "BUY",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "sl_distance": sd,
            "tp_distance": td,
            "rr": rr,
            "quality": quality,
            "reason": _build_reason(buy_setup, "BUY"),
            "valid": True,
        }

    return None