import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def detect_ny_breakout_signal(df_m5: pd.DataFrame) -> dict:
    """
    استراتژی NY Open Range Breakout (ORB).
    - بازه رنج: 9:30 تا 9:45 (15 دقیقه اول)
    - بازه بریک‌اوت: 9:45 تا 10:30 (45 دقیقه بعد)
    - DST با ZoneInfo دقیق
    """
    if len(df_m5) < 20:
        return None

    closed = df_m5.iloc[:-1]
    if len(closed) < 10:
        return None
    
    last_candle = closed.iloc[-1]
    
    dt = last_candle["datetime"]
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace(" ", "T"))
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    ny_tz = ZoneInfo("America/New_York")
    dt_ny = dt.astimezone(ny_tz)
    
    ny_hour = dt_ny.hour
    ny_min = dt_ny.minute
    
    # 🚨 بازه بریک‌اوت: 9:45 تا 10:30 (به جای 9:30-9:45)
    if not (ny_hour == 9 and 45 <= ny_min) and not (ny_hour == 10 and ny_min <= 30):
        return None
    
    # پیدا کردن رنج از 9:30 تا 9:45
    range_candles = []
    for idx, row in closed.iterrows():
        row_dt = row["datetime"]
        if isinstance(row_dt, str):
            row_dt = datetime.fromisoformat(row_dt.replace(" ", "T"))
        
        if row_dt.tzinfo is None:
            row_dt = row_dt.replace(tzinfo=timezone.utc)
        else:
            row_dt = row_dt.astimezone(timezone.utc)
        
        row_ny = row_dt.astimezone(ny_tz)
        
        # رنج: 9:30 تا 9:45
        if row_ny.hour == 9 and 30 <= row_ny.minute < 45:
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