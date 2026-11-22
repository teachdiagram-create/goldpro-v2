"""
Strategy: Correlation + Trend Confirmation
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd


def check_correlation(df_gold, df_dxy, window: int = 20) -> tuple[bool, float]:
    """
    بررسی همبستگی منفی بین طلا و دلار.
    دیتافریم‌ها به UTC تبدیل و بر اساس بازه‌های ۵ دقیقه‌ای هم‌تراز می‌شن.
    """
    if df_dxy is None or len(df_dxy) < window or len(df_gold) < window:
        return False, 0.0

    try:
        gold = df_gold[["datetime", "close"]].tail(window + 10).copy()
        dxy = df_dxy[["datetime", "close"]].tail(window + 10).copy()
        
        gold["datetime"] = pd.to_datetime(gold["datetime"])
        dxy["datetime"] = pd.to_datetime(dxy["datetime"])
        
        if gold["datetime"].dt.tz is None:
            gold["datetime"] = gold["datetime"].dt.tz_localize("UTC")
        else:
            gold["datetime"] = gold["datetime"].dt.tz_convert("UTC")
        
        if dxy["datetime"].dt.tz is None:
            dxy["datetime"] = dxy["datetime"].dt.tz_localize("UTC")
        else:
            dxy["datetime"] = dxy["datetime"].dt.tz_convert("UTC")
        
        # هم‌ترازی: زمان‌ها رو به نزدیک‌ترین ۵ دقیقه گرد می‌کنیم
        gold["time_5m"] = gold["datetime"].dt.floor("5min")
        dxy["time_5m"] = dxy["datetime"].dt.floor("5min")
        
        merged = pd.merge(
            gold[["time_5m", "close"]], 
            dxy[["time_5m", "close"]], 
            on="time_5m", 
            suffixes=("_gold", "_dxy")
        )
        
        if len(merged) < 10:
            return False, 0.0
        
        gold_ret = merged["close_gold"].pct_change().dropna()
        dxy_ret = merged["close_dxy"].pct_change().dropna()
        
        if len(gold_ret) < 5 or len(dxy_ret) < 5:
            return False, 0.0

        corr = float(gold_ret.corr(dxy_ret))
        is_valid = corr < -0.3
        return is_valid, round(corr, 3)
    except Exception as e:
        print(f"[!] check_correlation error: {e}")
        return False, 0.0


def check_news_blackout(dt_str: str) -> tuple[bool, str]:
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        if dt.hour == 12 and 30 <= dt.minute <= 59:
            return True, "News blackout (12:30-13:00 UTC)"
        if dt.hour == 13 and dt.minute <= 30:
            return True, "News blackout (13:00-13:30 UTC)"
        
        return False, "OK"
    except Exception:
        return False, "OK"


def check_trading_hours(dt_str: str) -> tuple[bool, str]:
    """
    فیلتر ساعت: لندن + نیویورک با استفاده از ZoneInfo (DST دقیق).
    """
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        
        # 🚨 محاسبه دقیق DST با ZoneInfo
        london_tz = ZoneInfo("Europe/London")
        ny_tz = ZoneInfo("America/New_York")
        
        dt_london = dt.astimezone(london_tz)
        dt_ny = dt.astimezone(ny_tz)
        
        # لندن: 8:00 تا 16:30 به وقت لندن
        in_london = 8 <= dt_london.hour < 16 or (dt_london.hour == 16 and dt_london.minute <= 30)
        
        # نیویورک: 9:30 تا 16:00 به وقت نیویورک
        in_ny = (dt_ny.hour == 9 and dt_ny.minute >= 30) or (10 <= dt_ny.hour < 16)
        
        if in_london and in_ny:
            return True, "London+NY overlap"
        if in_london:
            return True, "London session"
        if in_ny:
            return True, "New York session"
        
        return False, "Outside trading hours"
    
    except Exception as e:
        print(f"[!] check_trading_hours error: {e}")
        return False, "Invalid time"


def detect_trend_m15(df_m15) -> str:
    if len(df_m15) < 55:
        return "NONE"

    last = df_m15.iloc[-1]
    ema_fast = float(last["ema_fast"])
    ema_slow = float(last["ema_slow"])
    adx = float(last["adx"])

    if adx < 20:
        return "NONE"

    if ema_fast > ema_slow:
        return "BUY"
    elif ema_fast < ema_slow:
        return "SELL"
    return "NONE"


def detect_trigger_m5(df_m5, trend: str) -> bool:
    if len(df_m5) < 5:
        return False

    last = df_m5.iloc[-1]
    close = float(last["close"])
    ema_fast = float(last["ema_fast"])
    macd = float(last["macd"])
    macd_sig = float(last["macd_signal"])

    if trend == "BUY":
        return macd > macd_sig and close > ema_fast
    elif trend == "SELL":
        return macd < macd_sig and close < ema_fast
    return False