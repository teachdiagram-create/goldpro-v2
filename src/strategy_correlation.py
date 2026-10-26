"""
Strategy: Correlation + Trend Confirmation
- فیلتر همبستگی دلار (DXY)
- تشخیص روند در M15
- تریگر در M5
- فیلتر ساعت و خبر
"""
from datetime import datetime, timezone


def check_correlation(df_gold, df_dxy, window: int = 20) -> tuple[bool, float]:
    """
    بررسی همبستگی منفی بین طلا و دلار.
    Returns: (is_valid, corr_value)
    """
    if df_dxy is None or len(df_dxy) < window or len(df_gold) < window:
        return False, 0.0

    try:
        gold_close = df_gold["close"].tail(window + 1)
        dxy_close = df_dxy["close"].tail(window + 1)

        # همبستگی درصد تغییرات (نه قیمت خام)
        gold_ret = gold_close.pct_change().dropna()
        dxy_ret = dxy_close.pct_change().dropna()

        if len(gold_ret) < 5 or len(dxy_ret) < 5:
            return False, 0.0

        corr = float(gold_ret.corr(dxy_ret))
        
        # همبستگی منفی (زیر -0.3) معتبره
        is_valid = corr < -0.3
        return is_valid, round(corr, 3)
    except Exception:
        return False, 0.0


def check_news_blackout(dt_str: str) -> tuple[bool, str]:
    """
    فیلتر خبر: ۳۰ دقیقه قبل و بعد از اخبار مهم (ساختار ساده).
    فعلاً اخبار رو هاردکد می‌کنیم. بعداً می‌تونی از API بگیر.
    
    Returns: (is_blocked, reason)
    """
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # اخبار مهم اقتصادی (UTC) - برای تست
        # معمولاً: NFP (جمعه اول ماه), CPI (وسط ماه), FOMC (۸ بار در سال)
        # اینجا یه بازه‌ی کلی گذاشتیم: ۱۲:۳۰ تا ۱۳:۳۰ UTC (NFP/CPI)
        if dt.hour == 12 and 30 <= dt.minute <= 59:
            return True, "News blackout (12:30-13:00 UTC)"
        if dt.hour == 13 and dt.minute <= 30:
            return True, "News blackout (13:00-13:30 UTC)"
        
        return False, "OK"
    except Exception:
        return False, "OK"


from datetime import datetime, timezone

def check_trading_hours(dt_str: str) -> tuple[bool, str]:
    """
    فیلتر ساعت: لندن + نیویورک با در نظر گرفتن تغییرات DST.
    
    - لندن (GMT): 08:00 - 16:00 UTC در زمستان، 07:00 - 16:00 UTC در تابستان
    - نیویورک (EST): 13:00 - 21:00 UTC در زمستان، 12:00 - 21:00 UTC در تابستان
    """
    try:
        dt = datetime.fromisoformat(dt_str.replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        h = dt.hour
        month = dt.month
        day = dt.day
        
        # ─── تشخیص DST اروپا ───
        # اروپا: آخرین یکشنبه مارس تا آخرین یکشنبه اکتبر
        # ساده‌سازی: مارس (بعد از ۲۰) تا اکتبر (قبل از ۲۵) = تابستان
        europe_summer = (month > 3 and month < 10) or \
                        (month == 3 and day >= 20) or \
                        (month == 10 and day < 25)
        
        london_start = 7 if europe_summer else 8
        london_end = 16
        
        # ─── تشخیص DST آمریکا ───
        # آمریکا: دومین یکشنبه مارس تا اولین یکشنبه نوامبر
        # ساده‌سازی: مارس (بعد از ۸) تا نوامبر (قبل از ۱) = تابستان
        us_summer = (month > 3 and month < 11) or \
                    (month == 3 and day >= 8) or \
                    (month == 11 and day < 1)
        
        ny_start = 12 if us_summer else 13
        ny_end = 21
        
        # ─── چک بازه‌ها ───
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
        return False, "Invalid time""


def detect_trend_m15(df_m15) -> str:
    """
    تشخیص روند در M15.
    Returns: "BUY" | "SELL" | "NONE"
    """
    if len(df_m15) < 55:
        return "NONE"

    last = df_m15.iloc[-1]
    ema_fast = float(last["ema_fast"])
    ema_slow = float(last["ema_slow"])
    adx = float(last["adx"])

    # ADX باید بالای ۲۰ باشه (روند داره)
    if adx < 20:
        return "NONE"

    if ema_fast > ema_slow:
        return "BUY"
    elif ema_fast < ema_slow:
        return "SELL"
    return "NONE"


def detect_trigger_m5(df_m5, trend: str) -> bool:
    """
    تریگر ورود در M5 در جهت روند M15.
    BUY: MACD > signal + close > EMA20
    SELL: MACD < signal + close < EMA20
    """
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