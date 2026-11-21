import pandas as pd
from datetime import datetime, timezone


def detect_ny_breakout_signal(df_m5: pd.DataFrame) -> dict:
    """
    استراتژی NY Open Range Breakout (ORB) مخصوص XAUUSD در M5.
    فقط آخرین کندل بسته شده رو بررسی می‌کنه تا از تکرار جلوگیری بشه.
    """
    if len(df_m5) < 20:
        return None

    closed = df_m5.iloc[:-1]
    if len(closed) < 10:
        return None
    
    last_candle = closed.iloc[-1]
    
    now_utc = datetime.now(timezone.utc)
    month = now_utc.month
    is_dst = 3 < month < 11
    
    if is_dst:
        range_start_hour, range_start_minute = 13, 30
        entry_deadline_hour, entry_deadline_minute = 13, 45
    else:
        range_start_hour, range_start_minute = 14, 30
        entry_deadline_hour, entry_deadline_minute = 14, 45

    dt = last_candle["datetime"]
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace(" ", "T"))
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    range_start = dt.replace(hour=range_start_hour, minute=range_start_minute, second=0, microsecond=0)
    range_end = range_start.replace(minute=range_start_minute + 5)
    entry_deadline = dt.replace(hour=entry_deadline_hour, minute=entry_deadline_minute, second=0, microsecond=0)
    
    if not (range_end <= dt <= entry_deadline):
        return None
    
    range_candles = []
    for idx, row in closed.iterrows():
        row_dt = row["datetime"]
        if isinstance(row_dt, str):
            row_dt = datetime.fromisoformat(row_dt.replace(" ", "T"))
        if row_dt.tzinfo is None:
            row_dt = row_dt.replace(tzinfo=timezone.utc)
        
        if range_start <= row_dt < range_end:
            range_candles.append(row)
    
    if not range_candles:
        return None
    
    range_high = max([float(c["high"]) for c in range_candles])
    range_low = min([float(c["low"]) for c in range_candles])
    range_size = range_high - range_low
    
    if range_size < 1.0 or range_size > 15.0:
        return None
    
    candle_high = float(last_candle["high"])
    candle_low = float(last_candle["low"])
    candle_open = float(last_candle["open"])
    candle_close = float(last_candle["close"])
    
    body = abs(candle_close - candle_open)
    total_range = candle_high - candle_low
    
    if total_range <= 0:
        return None
    
    body_ratio = body / total_range
    if body_ratio < 0.6:
        return None
    
    recent = closed.tail(6).head(5)
    tr_list = []
    for i in range(1, len(recent)):
        h = float(recent.iloc[i]["high"])
        l = float(recent.iloc[i]["low"])
        pc = float(recent.iloc[i-1]["close"])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        tr_list.append(tr)
    atr_5 = sum(tr_list) / len(tr_list) if tr_list else 0.0
    
    if atr_5 <= 0 or body < atr_5:
        return None
    
    if candle_close > range_high and candle_close > candle_open:
        return {
            "pattern": "ny_orb_breakout_buy",
            "strategy": "NY_BREAKOUT",
            "direction": "BUY",
            "entry": round(candle_close, 2),
            "sl_candle_low": round(candle_low, 2),
            "range_high": round(range_high, 2),
            "range_low": round(range_low, 2),
            "candle_high": round(candle_high, 2),
        }
    
    if candle_close < range_low and candle_close < candle_open:
        return {
            "pattern": "ny_orb_breakout_sell",
            "strategy": "NY_BREAKOUT",
            "direction": "SELL",
            "entry": round(candle_close, 2),
            "sl_candle_high": round(candle_high, 2),
            "range_high": round(range_high, 2),
            "range_low": round(range_low, 2),
            "candle_low": round(candle_low, 2),
        }
    
    return None