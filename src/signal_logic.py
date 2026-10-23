"""
Signal Logic - Interface between strategies and infrastructure.

استراتژی‌های موجود:
1. RANGE: RSI Double Top/Bottom
2. TREND: EMA Cross + MACD
3. (اینجا استراتژی جدید اضافه کن)
"""
from src.config import compute_sl_tp
from src.strategy import (
    detect_double_top_sell,
    detect_double_bottom_buy,
    detect_trend_signal,
)


def _compute_quality(adx_val: float, atr_val: float,
                     rsi_val: float, side: str, strategy: str) -> dict:
    score = 50
    flags = []
    warnings = []

    # ADX
    if adx_val is None:
        warnings.append("ADX نامشخص")
    elif adx_val >= 50:
        score += 30; flags.append("ADX قوی")
    elif adx_val >= 35:
        score += 20; flags.append("ADX خوب")
    elif adx_val >= 25:
        score += 10
    elif adx_val >= 15:
        score -= 5; warnings.append("ADX ضعیف")
    else:
        score -= 20; warnings.append("ADX خیلی ضعیف")

    # ATR
    if atr_val is None:
        warnings.append("ATR نامشخص")
    elif atr_val < 0.5:
        score -= 25; warnings.append("ATR خیلی کم")
    elif atr_val < 1.0:
        score -= 10; warnings.append("ATR کم")
    elif atr_val <= 4.0:
        score += 10; flags.append("ATR مناسب")
    elif atr_val <= 6.0:
        score -= 5; warnings.append("ATR بالا")
    else:
        score -= 15; warnings.append("ATR خیلی بالا")

    # RSI
    if rsi_val is not None:
        if strategy == "RANGE":
            if side == "SELL" and rsi_val <= 65:
                score += 10; flags.append("RSI تأیید می‌کند")
            elif side == "BUY" and rsi_val >= 35:
                score += 10; flags.append("RSI تأیید می‌کند")
            elif side == "SELL" and rsi_val >= 70:
                score -= 10; warnings.append("RSI هنوز بالا")
            elif side == "BUY" and rsi_val <= 30:
                score -= 10; warnings.append("RSI هنوز پایین")
        elif strategy == "TREND":
            if side == "BUY" and 40 <= rsi_val <= 70:
                score += 10; flags.append("RSI در محدوده")
            elif side == "SELL" and 30 <= rsi_val <= 60:
                score += 10; flags.append("RSI در محدوده")

    score = max(0, min(100, score))
    if score >= 80: grade = "A"
    elif score >= 65: grade = "B"
    elif score >= 50: grade = "C"
    else: grade = "D"

    return {"score": score, "grade": grade, "flags": flags, "warnings": warnings}


def _build_reason(setup: dict, side: str, strategy: str) -> str:
    if strategy == "RANGE":
        if side == "SELL":
            p1 = setup.get("peak1_value")
            p2 = setup.get("peak2_value")
            cur = setup.get("current_rsi")
            if p1 is not None and p2 is not None:
                return f"RSI double top: {p1} -> {p2} (now {cur})"
        elif side == "BUY":
            t1 = setup.get("trough1_value")
            t2 = setup.get("trough2_value")
            cur = setup.get("current_rsi")
            if t1 is not None and t2 is not None:
                return f"RSI double bottom: {t1} -> {t2} (now {cur})"
    elif strategy == "TREND":
        ef = setup.get("ema_fast")
        es = setup.get("ema_slow")
        return f"EMA Cross ({ef} vs {es}) + MACD"
    
    return setup.get("reason", f"{side} signal")


def evaluate_signal(df, timeframe: str = "5min"):
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
    #  لیست استراتژی‌ها (پویا)
    #  برای اضافه کردن استراتژی جدید، فقط این لیست رو گسترش بده
    # ══════════════════════════════════════════
    strategies_to_check = []

    # 1. RANGE
    sell_setup = detect_double_top_sell(rsi_series)
    if sell_setup:
        strategies_to_check.append(("SELL", sell_setup, "RANGE"))

    buy_setup = detect_double_bottom_buy(rsi_series)
    if buy_setup:
        strategies_to_check.append(("BUY", buy_setup, "RANGE"))

    # 2. TREND
    trend_signal = detect_trend_signal(closed)
    if trend_signal:
        strategies_to_check.append((trend_signal["direction"], trend_signal, "TREND"))

    # 3. BREAKOUT (مثال برای آینده)
    # breakout_signal = detect_breakout(closed)
    # if breakout_signal:
    #     strategies_to_check.append((breakout_signal["direction"], breakout_signal, "BREAKOUT"))

    # حالا اولین سیگنال معتبر رو برگردون
    for side, setup, strategy in strategies_to_check:
        sl, tp, sd, td, rr = compute_sl_tp(side, price, atr_)
        if sl is None:
            continue

        quality = _compute_quality(adx_, atr_, rsi_, side, strategy)

        return {
            **base,
            "side": side,
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "sl_distance": sd,
            "tp_distance": td,
            "rr": rr,
            "strategy": strategy,
            "quality": quality,
            "reason": _build_reason(setup, side, strategy),
            "valid": True,
        }

    return None