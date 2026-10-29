from datetime import datetime, timezone, timedelta

from src.config import (
    compute_sl_tp, SL_CORR_MULT, TP_CORR_MULT, MAX_SL_USD,
    SL_ICHI_MULT, TP_ICHI_MULT, MIN_SL_USD, MIN_TP_USD
)
from src.strategy import (
    detect_double_top_sell,
    detect_double_bottom_buy,
    detect_trend_signal,
)
from src.strategy_correlation import (
    check_correlation,
    check_news_blackout,
    check_trading_hours,
    detect_trend_m15,
    detect_trigger_m5,
)
from src.strategy_ichimoku import detect_ichimoku_signal


def _is_market_closed_or_opening(dt_str: str) -> bool:
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        weekday = dt.weekday()
        hour = dt.hour
        if weekday == 5: return True
        if weekday == 6 and hour < 23: return True
        if weekday == 4 and hour >= 21: return True
        return False
    except Exception:
        return False


def _compute_quality(adx_val: float, atr_val: float, rsi_val: float, side: str, strategy: str) -> dict:
    score = 50
    flags = []
    warnings = []

    if adx_val is None: warnings.append("ADX نامشخص")
    elif adx_val >= 50: score += 30; flags.append("ADX قوی")
    elif adx_val >= 35: score += 20; flags.append("ADX خوب")
    elif adx_val >= 25: score += 10
    elif adx_val >= 15: score -= 5; warnings.append("ADX ضعیف")
    else: score -= 20; warnings.append("ADX خیلی ضعیف")

    if atr_val is None: warnings.append("ATR نامشخص")
    elif atr_val < 0.5: score -= 25; warnings.append("ATR خیلی کم")
    elif atr_val < 1.0: score -= 10; warnings.append("ATR کم")
    elif atr_val <= 4.0: score += 10; flags.append("ATR مناسب")
    elif atr_val <= 6.0: score -= 5; warnings.append("ATR بالا")
    else: score -= 15; warnings.append("ATR خیلی بالا")

    if rsi_val is not None:
        if strategy == "RANGE":
            if side == "SELL" and rsi_val <= 65: score += 10; flags.append("RSI تأیید می‌کند")
            elif side == "BUY" and rsi_val >= 35: score += 10; flags.append("RSI تأیید می‌کند")
        elif strategy in ("TREND", "CORRELATION", "ICHIMOKU"):
            if side == "BUY" and 40 <= rsi_val <= 70: score += 10; flags.append("RSI در محدوده")
            elif side == "SELL" and 30 <= rsi_val <= 60: score += 10; flags.append("RSI در محدوده")

    score = max(0, min(100, score))
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"
    return {"score": score, "grade": grade, "flags": flags, "warnings": warnings}


def _build_reason(setup: dict, side: str, strategy: str) -> str:
    if strategy == "RANGE":
        if side == "SELL":
            return f"RSI double top: {setup.get('peak1_value')} -> {setup.get('peak2_value')}"
        else:
            return f"RSI double bottom: {setup.get('trough1_value')} -> {setup.get('trough2_value')}"
    elif strategy == "TREND":
        return "EMA Cross + MACD"
    elif strategy == "CORRELATION":
        return f"DXY corr + M15 trend {side} + M5 trigger"
    elif strategy == "ICHIMOKU":
        return f"Ichimoku cross (Tenkan/Kijun) + cloud confirm"
    return f"{side} signal"


def evaluate_signal(df_m5, df_m15, df_dxy_m5=None, df_dxy_m15=None):
    # آماده‌سازی M5
    closed_m5 = df_m5.iloc[:-1]
    current_m5 = closed_m5.iloc[-1]

    price = float(current_m5["close"])
    atr_ = float(current_m5["atr"])
    adx_ = float(current_m5["adx"])
    rsi_ = float(current_m5["rsi"])

    dt_raw = current_m5["datetime"]
    if isinstance(dt_raw, str):
        dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
    else:
        dt_obj = dt_raw
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    
    closed_time = dt_obj + timedelta(minutes=5)
    dt_str = closed_time.isoformat()

    if _is_market_closed_or_opening(dt_str):
        return None

    base = {
        "timeframe": "5min",
        "rsi": round(rsi_, 1),
        "adx": round(adx_, 1),
        "atr": round(atr_, 2),
        "time": dt_str,
    }

    # ─── استراتژی ۱: CORRELATION ───
    if df_dxy_m5 is not None and len(df_dxy_m5) > 20 and df_m15 is not None:
        hour_ok, _ = check_trading_hours(dt_str)
        news_blocked, _ = check_news_blackout(dt_str)
        if hour_ok and not news_blocked:
            trend = detect_trend_m15(df_m15.iloc[:-1])
            if trend in ("BUY", "SELL"):
                corr_ok, corr_val = check_correlation(df_m5, df_dxy_m5)
                trigger_ok = detect_trigger_m5(closed_m5, trend)
                if corr_ok and trigger_ok:
                    sl_dist = min(max(SL_CORR_MULT * atr_, 3.0), MAX_SL_USD)
                    tp_dist = min(max(TP_CORR_MULT * atr_, 4.5), MAX_SL_USD * 1.5)
                    sl = round(price + sl_dist if trend == "SELL" else price - sl_dist, 2)
                    tp = round(price - tp_dist if trend == "SELL" else price + tp_dist, 2)
                    return {
                        **base, "side": trend, "entry": round(price, 2),
                        "sl": sl, "tp": tp, "sl_distance": round(sl_dist, 2), "tp_distance": round(tp_dist, 2), "rr": round(tp_dist/sl_dist, 2),
                        "strategy": "CORRELATION",
                        "quality": _compute_quality(adx_, atr_, rsi_, trend, "CORRELATION"),
                        "reason": f"DXY corr={corr_val} + M15 {trend} + M5 trigger",
                        "valid": True,
                    }

    # ─── استراتژی ۲: RANGE ───
    sell_setup = detect_double_top_sell(closed_m5["rsi"])
    if sell_setup:
        sl, tp, sd, td, rr = compute_sl_tp("SELL", price, atr_)
        if sl is not None:
            return {
                **base, "side": "SELL", "entry": round(price, 2),
                "sl": sl, "tp": tp, "sl_distance": sd, "tp_distance": td, "rr": rr,
                "strategy": "RANGE",
                "quality": _compute_quality(adx_, atr_, rsi_, "SELL", "RANGE"),
                "reason": _build_reason(sell_setup, "SELL", "RANGE"),
                "valid": True,
            }

    buy_setup = detect_double_bottom_buy(closed_m5["rsi"])
    if buy_setup:
        sl, tp, sd, td, rr = compute_sl_tp("BUY", price, atr_)
        if sl is not None:
            return {
                **base, "side": "BUY", "entry": round(price, 2),
                "sl": sl, "tp": tp, "sl_distance": sd, "tp_distance": td, "rr": rr,
                "strategy": "RANGE",
                "quality": _compute_quality(adx_, atr_, rsi_, "BUY", "RANGE"),
                "reason": _build_reason(buy_setup, "BUY", "RANGE"),
                "valid": True,
            }

    # ─── استراتژی ۳: TREND ───
    trend_signal = detect_trend_signal(closed_m5)
    if trend_signal:
        side = trend_signal["direction"]
        sl, tp, sd, td, rr = compute_sl_tp(side, price, atr_)
        if sl is not None:
            return {
                **base, "side": side, "entry": round(price, 2),
                "sl": sl, "tp": tp, "sl_distance": sd, "tp_distance": td, "rr": rr,
                "strategy": "TREND",
                "quality": _compute_quality(adx_, atr_, rsi_, side, "TREND"),
                "reason": _build_reason(trend_signal, side, "TREND"),
                "valid": True,
            }

    # ─── استراتژی ۴: ICHIMOKU ───
    ichi_signal = detect_ichimoku_signal(df_m5) # نکته: کل df_m5 رو پاس می‌دیم
    if ichi_signal:
        side = ichi_signal["direction"]
        sl_dist = min(max(SL_ICHI_MULT * atr_, MIN_SL_USD), MAX_SL_USD)
        tp_dist = min(max(TP_ICHI_MULT * atr_, MIN_TP_USD), MAX_SL_USD * 1.5)
        sl = round(price + sl_dist if side == "SELL" else price - sl_dist, 2)
        tp = round(price - tp_dist if side == "SELL" else price + tp_dist, 2)
        return {
            **base, "side": side, "entry": round(price, 2),
            "sl": sl, "tp": tp, "sl_distance": round(sl_dist, 2), "tp_distance": round(tp_dist, 2), "rr": round(tp_dist/sl_dist, 2),
            "strategy": "ICHIMOKU",
            "quality": _compute_quality(adx_, atr_, rsi_, side, "ICHIMOKU"),
            "reason": _build_reason(ichi_signal, side, "ICHIMOKU"),
            "valid": True,
        }

    return None