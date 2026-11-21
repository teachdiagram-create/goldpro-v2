"""
Strategy: Correlation + Trend Confirmation
"""
from datetime import datetime, timezone
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
        
        # تبدیل به datetime
        gold["datetime"] = pd.to_datetime(gold["datetime"])
        dxy["datetime"] = pd.to_datetime(dxy["datetime"])
        
        # تبدیل به UTC
        if gold["datetime"].dt.tz is None:
            gold["datetime"] = gold["datetime"].dt.tz_localize("UTC")
        else:
            gold["datetime"] = gold["datetime"].dt.tz_convert("UTC")
        
        if dxy["datetime"].dt.tz is None:
            dxy["datetime"] = dxy["datetime"].dt.tz_localize("UTC")
        else:
            dxy["datetime"] = dxy["datetime"].dt.tz_convert("UTC")
        
        # 🚨 هم‌ترازی: زمان‌ها رو به نزدیک‌ترین ۵ دقیقه گرد می‌کنیم
        gold["time_5m"] = gold["datetime"].dt.floor("5min")
        dxy["time_5m"] = dxy["datetime"].dt.floor("5min")
        
        # merge بر اساس زمان ۵ دقیقه‌ای
        merged = pd.merge(
            gold[["time_5m", "close"]], 
            dxy[["time_5m", "close"]], 
            on="time_5m", 
            suffixes=("_gold", "_dxy")
        )
        
        if len(merged) < 10:
            return False, 0.0
        
        # محاسبه درصد تغییرات
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
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        h = dt.hour
        month = dt.month
        day = dt.day
        
        europe_summer = (month > 3 and month < 10) or \
                        (month == 3 and day >= 20) or \
                        (month == 10 and day < 25)
        
        london_start = 7 if europe_summer else 8
        london_end = 16
        
        us_summer = (month > 3 and month < 11) or \
                    (month == 3 and day >= 8) or \
                    (month == 11 and day < 1)
        
        ny_start = 12 if us_summer else 13
        ny_end = 21
        
        in_london = london_start <= h < london_end
        in_ny = ny_start <= h < ny_end
        in_overlap = in_london and in_ny
        
        if in_overlap:
            return True, f"London+NY overlap (UTC {h:02d})"
        if in_london:
            return True, f"London session (UTC {h:02d})"
        if in_ny:
            return True, f"New York session (UTC {h:02d})"
        
        return False, f"Outside trading hours (UTC {h:02d})"
    
    except Exception:
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