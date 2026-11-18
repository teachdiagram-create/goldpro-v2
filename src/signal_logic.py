from datetime import datetime, timezone, timedelta

from src.config import (
    compute_sl_tp, SL_CORR_MULT, TP_CORR_MULT, MAX_SL_USD,
    SL_ICHI_MULT, TP_ICHI_MULT, MIN_SL_USD, MIN_TP_USD
)
from src.strategy import (
    detect_double_top_sell,
    detect_double_bottom_buy,
    detect_trend_signal,
    check_divergence,
)
from src.strategy_correlation import (
    check_correlation,
    check_news_blackout,
    check_trading_hours,
    detect_trend_m15,
    detect_trigger_m5,
)
from src.strategy_ichimoku import detect_ichimoku_signal
from src.strategy_ny_breakout import detect_ny_breakout_signal
from src.strategy_v6 import detect_v6_signal


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


def _compute_quality(adx_val: float, atr_val: float, rsi_val: float, 
                     side: str, strategy: str, divergence: bool = False) -> dict:
    # ... (همون کد وزنی که تو پیام‌های قبل دادم)
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
        elif strategy in ("TREND", "CORRELATION", "ICHIMOKU", "NY_BREAKOUT", "V6_STRUCTURE"):
            if side == "BUY" and 40 <= rsi_val <= 70: score += 10; flags.append("RSI در محدوده")
            elif side == "SELL" and 30 <= rsi_val <= 60: score += 10; flags.append("RSI در محدوده")

    if divergence:
        score += 15
        flags.append("واگرایی تایید شد")

    score = max(0, min(100, score))
    if score >= 80: grade = "A"
    elif score >= 65: grade = "B"
    elif score >= 50: grade = "C"
    else: grade = "D"
    return {"score": score, "grade": grade, "flags": flags, "warnings": warnings}


def _build_reason(setup: dict, side: str, strategy: str) -> str:
    # ... (همون کد قبلی)
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
        return "Ichimoku cross (Tenkan/Kijun) - Inverted"
    elif strategy == "NY_BREAKOUT":
        return f"NY ORB {side}: Range {setup.get('range_low')}-{setup.get('range_high')}"
    elif strategy == "V6_STRUCTURE":
        return f"V6 Structure {side}: Trend {setup.get('structure_trend')}"
    return f"{side} signal"


def evaluate_signal(df_m5, df_m15, df_dxy_m5=None, df_dxy_m15=None):
    closed_m5 = df_m5.iloc[:-1]
    current_m5 = closed_m5.iloc[-1]
    rsi_series_m5 = closed_m5["rsi"]

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

    timestamp_id = closed_time.strftime("%Y%m%d-%H%M")

    base = {
        "timeframe": "5min",
        "rsi": round(rsi_, 1),
        "adx": round(adx_, 1),
        "atr": round(atr_, 2),
        "time": dt_str,
    }

    valid_signals = []

    # ─── استراتژی ۰: NY ORB BREAKOUT ───
    ny_signal = detect_ny_breakout_signal(df_m5)
    if ny_signal:
        side = ny_signal["direction"]
        if side == "BUY":
            sl_price = ny_signal["sl_candle_low"]
            sl_dist = price - sl_price
            tp_dist = sl_dist * 2.5
            tp = round(price + tp_dist, 2)
            sl = round(sl_price, 2)
        else:
            sl_price = ny_signal["sl_candle_high"]
            sl_dist = sl_price - price
            tp_dist = sl_dist * 2.5
            tp = round(price - tp_dist, 2)
            sl = round(sl_price, 2)
        
        if 1.0 <= sl_dist <= 10.0:
            rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0
            q = _compute_quality(adx_, atr_, rsi_, side, "NY_BREAKOUT")
            valid_signals.append({
                **base, "signal_id": f"N-{timestamp_id}",
                "side": side, "entry": round(price, 2),
                "sl": sl, "tp": tp, "sl_distance": round(sl_dist, 2), "tp_distance": round(tp_dist, 2), "rr": rr,
                "strategy": "NY_BREAKOUT",
                "quality": q,
                "reason": _build_reason(ny_signal, side, "NY_BREAKOUT"),
                "valid": True,
                "_score": q["score"]
            })

    # ─── استراتژی V6 ───
    v6_signal = detect_v6_signal(df_m5, df_m15)
    if v6_signal:
        side = v6_signal["direction"]
        if side == "BUY":
            sl_price = v6_signal["local_low"] - (0.5 * atr_)
            sl_dist = price - sl_price
            if 1.0 <= sl_dist <= 15.0:
                tp_dist = sl_dist * 1.5
                tp = round(price + tp_dist, 2)
                sl = round(sl_price, 2)
                rr = round(tp_dist / sl_dist, 2)
                if rr >= 1.5:
                    q = _compute_quality(adx_, atr_, rsi_, side, "V6_STRUCTURE")
                    valid_signals.append({
                        **base, "signal_id": f"V6-{timestamp_id}",
                        "side": side, "entry": round(price, 2),
                        "sl": sl, "tp": tp, "sl_distance": round(sl_dist, 2), "tp_distance": round(tp_dist, 2), "rr": rr,
                        "strategy": "V6_STRUCTURE",
                        "quality": q,
                        "reason": _build_reason(v6_signal, side, "V6_STRUCTURE"),
                        "valid": True,
                        "_score": q["score"]
                    })
        else:
            sl_price = v6_signal["local_high"] + (0.5 * atr_)
            sl_dist = sl_price - price
            if 1.0 <= sl_dist <= 15.0:
                tp_dist = sl_dist * 1.5
                tp = round(price - tp_dist, 2)
                sl = round(sl_price, 2)
                rr = round(tp_dist / sl_dist, 2)
                if rr >= 1.5:
                    q = _compute_quality(adx_, atr_, rsi_, side, "V6_STRUCTURE")
                    valid_signals.append({
                        **base, "signal_id": f"V6-{timestamp_id}",
                        "side": side, "entry": round(price, 2),
                        "sl": sl, "tp": tp, "sl_distance": round(sl_dist, 2), "tp_distance": round(tp_dist, 2), "rr": rr,
                        "strategy": "V6_STRUCTURE",
                        "quality": q,
                        "reason": _build_reason(v6_signal, side, "V6_STRUCTURE"),
                        "valid": True,
                        "_score": q["score"]
                    })

    # ─── استراتژی CORRELATION ───
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
                    q = _compute_quality(adx_, atr_, rsi_, trend, "CORRELATION")
                    valid_signals.append({
                        **base, "signal_id": f"C-{timestamp_id}",
                        "side": trend, "entry": round(price, 2),
                        "sl": sl, "tp": tp, "sl_distance": round(sl_dist, 2), "tp_distance": round(tp_dist, 2), "rr": round(tp_dist/sl_dist, 2),
                        "strategy": "CORRELATION",
                        "quality": q,
                        "reason": f"DXY corr={corr_val} + M15 {trend} + M5 trigger",
                        "valid": True,
                        "_score": q["score"]
                    })

    # ─── استراتژی RANGE ───
    if adx_ < 30:
        sell_setup = detect_double_top_sell(rsi_series_m5)
        if sell_setup:
            sl, tp, sd, td, rr = compute_sl_tp("SELL", price, atr_)
            if sl is not None:
                divergence = check_divergence(closed_m5, "SELL")
                q = _compute_quality(adx_, atr_, rsi_, "SELL", "RANGE", divergence)
                valid_signals.append({
                    **base, "signal_id": f"R-{timestamp_id}",
                    "side": "SELL", "entry": round(price, 2),
                    "sl": sl, "tp": tp, "sl_distance": sd, "tp_distance": td, "rr": rr,
                    "strategy": "RANGE",
                    "quality": q,
                    "reason": _build_reason(sell_setup, "SELL", "RANGE"),
                    "valid": True,
                    "_score": q["score"]
                })

        buy_setup = detect_double_bottom_buy(rsi_series_m5)
        if buy_setup:
            sl, tp, sd, td, rr = compute_sl_tp("BUY", price, atr_)
            if sl is not None:
                divergence = check_divergence(closed_m5, "BUY")
                q = _compute_quality(adx_, atr_, rsi_, "BUY", "RANGE", divergence)
                valid_signals.append({
                    **base, "signal_id": f"R-{timestamp_id}",
                    "side": "BUY", "entry": round(price, 2),
                    "sl": sl, "tp": tp, "sl_distance": sd, "tp_distance": td, "rr": rr,
                    "strategy": "RANGE",
                    "quality": q,
                    "reason": _build_reason(buy_setup, "BUY", "RANGE"),
                    "valid": True,
                    "_score": q["score"]
                })

    # ─── استراتژی TREND ───
    trend_signal = detect_trend_signal(closed_m5)
    if trend_signal:
        side = trend_signal["direction"]
        sl, tp, sd, td, rr = compute_sl_tp(side, price, atr_)
        if sl is not None:
            q = _compute_quality(adx_, atr_, rsi_, side, "TREND")
            valid_signals.append({
                **base, "signal_id": f"T-{timestamp_id}",
                "side": side, "entry": round(price, 2),
                "sl": sl, "tp": tp, "sl_distance": sd, "tp_distance": td, "rr": rr,
                "strategy": "TREND",
                "quality": q,
                "reason": _build_reason(trend_signal, side, "TREND"),
                "valid": True,
                "_score": q["score"]
            })

    # ─── استراتژی ICHIMOKU ───
    ichi_signal = detect_ichimoku_signal(df_m5)
    if ichi_signal:
        side = ichi_signal["direction"]
        sl_dist = min(max(SL_ICHI_MULT * atr_, MIN_SL_USD), MAX_SL_USD)
        tp_dist = min(max(TP_ICHI_MULT * atr_, MIN_TP_USD), MAX_SL_USD * 1.5)
        if side == "SELL":
            sl = round(price + sl_dist, 2)
            tp = round(price - tp_dist, 2)
        else:
            sl = round(price - sl_dist, 2)
            tp = round(price + tp_dist, 2)
        rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0
        q = _compute_quality(adx_, atr_, rsi_, side, "ICHIMOKU")
        valid_signals.append({
            **base, "signal_id": f"I-{timestamp_id}",
            "side": side, "entry": round(price, 2),
            "sl": sl, "tp": tp, "sl_distance": round(sl_dist, 2), "tp_distance": round(tp_dist, 2), "rr": rr,
            "strategy": "ICHIMOKU",
            "quality": q,
            "reason": _build_reason(ichi_signal, side, "ICHIMOKU"),
            "valid": True,
            "_score": q["score"]
        })

    # ─── 🚨 انتخاب بهترین سیگنال با بررسی جهت‌های متناقض ───
    if not valid_signals:
        return None

    # ۱. بررسی اینکه آیا سیگنال‌های متناقض وجود دارن
    buy_signals = [s for s in valid_signals if s["side"] == "BUY"]
    sell_signals = [s for s in valid_signals if s["side"] == "SELL"]

    if buy_signals and sell_signals:
        # 🚨 سیگنال‌های متناقض داریم: هیچ‌کدوم رو انتخاب نکن (محافظه‌کارانه)
        print(f"⚠️ Contradictory signals detected: {len(buy_signals)} BUY vs {len(sell_signals)} SELL - Skipping")
        return None

    # ۲. اگه همه هم‌جهت بودن، بهترین رو انتخاب کن
    valid_signals.sort(key=lambda x: x["_score"], reverse=True)
    best_signal = valid_signals[0]
    del best_signal["_score"]
    return best_signal