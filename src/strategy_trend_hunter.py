import pandas as pd


def detect_trend_hunter_signal(df_m5: pd.DataFrame, df_m15: pd.DataFrame) -> dict:
    """
    استراتژی Trend Hunter: شکار روندهای قوی با پولبک به EMA.
    
    - فیلتر روند (M15): ADX > 30، قیمت زیر EMA200 (برای فروش) یا بالای EMA200 (برای خرید).
    - تریگر (M5): پولبک به EMA20/50 و بسته شدن کندل تایید در جهت روند.
    """
    if len(df_m15) < 60 or len(df_m5) < 30:
        return None

    # ─── ۱. فیلتر روند در M15 ───
    closed_m15 = df_m15.iloc[:-1]
    last_m15 = closed_m15.iloc[-1]
    price_m15 = float(last_m15["close"])
    adx_m15 = float(last_m15["adx"])
    ema50_m15 = float(last_m15["ema_slow"]) if "ema_slow" in last_m15 else price_m15
    
    # محاسبه EMA200 واقعی در M15
    if len(closed_m15) >= 200:
        from src.indicators import ema
        ema200_m15 = float(ema(closed_m15["close"], 200).iloc[-1])
    else:
        ema200_m15 = ema50_m15

    # ─── ۲. تریگر در M5 ───
    closed_m5 = df_m5.iloc[:-1]
    last_m5 = closed_m5.iloc[-1]
    prev_m5 = closed_m5.iloc[-2]
    
    price = float(last_m5["close"])
    open_price = float(last_m5["open"])
    high = float(last_m5["high"])
    low = float(last_m5["low"])
    atr_ = float(last_m5["atr"])
    
    ema20_m5 = float(last_m5["ema_fast"]) if "ema_fast" in last_m5 else price
    ema50_m5 = float(last_m5["ema_slow"]) if "ema_slow" in last_m5 else price

    # ─── ۳. منطق فروش (روند نزولی قوی) ───
    # شرط روند: ADX > 30 و قیمت زیر EMA200
    if adx_m15 > 30 and price_m15 < ema200_m15:
        # شرط پولبک: کندل قبلی نزولی نبوده و قیمت به EMA20 نزدیک شده
        # (یعنی یه استراحت کوتاه تو روند نزولی)
        distance_to_ema20 = abs(prev_m5["close"] - float(prev_m5["ema_fast"]))
        
        # کندل فعلی باید نزولی باشه و بدنه‌ش قوی باشه
        is_bearish = price < open_price
        body_size = abs(open_price - price)
        
        if is_bearish and body_size > 0.5 * atr_ and distance_to_ema20 < 1.0 * atr_:
            # محاسبه SL و TP
            sl_price = high + (0.5 * atr_) # SL بالای سقف کندل
            sl_dist = sl_price - price
            if 1.0 <= sl_dist <= 15.0:
                tp_dist = sl_dist * 2.0 # R:R = 2
                tp = round(price - tp_dist, 2)
                sl = round(sl_price, 2)
                
                return {
                    "pattern": "trend_hunter_sell",
                    "strategy": "TREND_HUNTER",
                    "direction": "SELL",
                    "entry": round(price, 2),
                    "sl": sl,
                    "tp": tp,
                    "sl_distance": round(sl_dist, 2),
                    "tp_distance": round(tp_dist, 2),
                    "rr": round(tp_dist / sl_dist, 2),
                }

    # ─── ۴. منطق خرید (روند صعودی قوی) ───
    if adx_m15 > 30 and price_m15 > ema200_m15:
        distance_to_ema20 = abs(prev_m5["close"] - float(prev_m5["ema_fast"]))
        
        is_bullish = price > open_price
        body_size = abs(price - open_price)
        
        if is_bullish and body_size > 0.5 * atr_ and distance_to_ema20 < 1.0 * atr_:
            sl_price = low - (0.5 * atr_)
            sl_dist = price - sl_price
            if 1.0 <= sl_dist <= 15.0:
                tp_dist = sl_dist * 2.0
                tp = round(price + tp_dist, 2)
                sl = round(sl_price, 2)
                
                return {
                    "pattern": "trend_hunter_buy",
                    "strategy": "TREND_HUNTER",
                    "direction": "BUY",
                    "entry": round(price, 2),
                    "sl": sl,
                    "tp": tp,
                    "sl_distance": round(sl_dist, 2),
                    "tp_distance": round(tp_dist, 2),
                    "rr": round(tp_dist / sl_dist, 2),
                }

    return None