import pandas as pd
from datetime import datetime, timezone

def detect_ny_breakout_signal(df_m5: pd.DataFrame) -> dict:
    """
    استراتژی NY Open Range Breakout (ORB) مخصوص XAUUSD در M5.
    - رنج: 9:30 تا 9:35 به وقت نیویورک
    - ورود: اولین کندل معتبر که با بدنه‌ی قوی بیرون رنج بسته بشه.
    - فقط تا ساعت 9:45 نیویورک اجازه ورود داریم.
    """
    if len(df_m5) < 20:
        return None

    # ۱. تشخیص ساعت تابستانی/زمستانی نیویورک (تقریبی بر اساس ماه)
    # برای دقت بیشتر می‌تونیم از pytz استفاده کنیم، ولی برای سادگی از تقویم استفاده می‌کنیم
    # در بازه مارس تا نوامبر (تقریباً) تابستانی (EDT=UTC-4)، بقیه زمستانی (EST=UTC-5)
    now_utc = datetime.now(timezone.utc)
    month = now_utc.month
    
    # تشخیص تقریبی DST (ساده شده)
    is_dst = 3 < month < 11  # (مارس تا اکتبر/نوامبر)
    
    # ساعت شروع رنج و مهلت ورود به UTC
    if is_dst:
        range_start_hour = 13  # 13:30 UTC
        range_start_minute = 30
        entry_deadline_hour = 13
        entry_deadline_minute = 45
    else:
        range_start_hour = 14  # 14:30 UTC
        range_start_minute = 30
        entry_deadline_hour = 14
        entry_deadline_minute = 45

    # ۲. پیدا کردن کندل‌های مربوط به رنج و بریک‌اوت
    # نکته: ما به آخرین کندل‌های بسته شده نگاه می‌کنیم
    closed = df_m5.iloc[:-1].copy()
    if len(closed) < 10:
        return None

    # پیدا کردن کندل‌های 9:30 تا 9:35 (رنج)
    # و کندل‌هایی که بعد از اون اومدن (تا 9:45)
    range_candles = []
    potential_breakout_candles = []
    
    for idx, row in closed.iterrows():
        dt = row["datetime"]
        # تبدیل به datetime اگه string بود
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace(" ", "T"))
        
        # چک کردن اینکه تو بازه‌ی رنج هستیم یا نه
        candle_hour = dt.hour
        candle_min = dt.minute
        
        # ساخت بازه‌ی زمانی رنج
        range_start = dt.replace(hour=range_start_hour, minute=range_start_minute, second=0, microsecond=0)
        range_end = range_start.replace(minute=range_start_minute + 5)
        
        entry_deadline = dt.replace(hour=entry_deadline_hour, minute=entry_deadline_minute, second=0, microsecond=0)
        
        # اگه کندل تو بازه‌ی رنج بود
        if range_start <= dt < range_end:
            range_candles.append(row)
        # اگه بعد از رنج بود و هنوز مهلت ورود تموم نشده
        elif range_end <= dt <= entry_deadline:
            potential_breakout_candles.append(row)

    # اگه رنج تشکیل نشده یا کندل بریک‌اوت نداریم
    if len(range_candles) == 0 or len(potential_breakout_candles) == 0:
        return None

    # محاسبه‌ی سقف و کف رنج
    range_high = max([float(c["high"]) for c in range_candles])
    range_low = min([float(c["low"]) for c in range_candles])
    range_size = range_high - range_low

    # فیلتر اندازه رنج (اگه رنج خیلی بزرگ یا خیلی کوچیک بود، نادیده بگیر)
    # مثلاً رنج نباید کمتر از 1 دلار یا بیشتر از 15 دلار باشه (قابل تنظیم)
    if range_size < 1.0 or range_size > 15.0:
        return None

    # ۳. بررسی کندل‌های بریک‌اوت (فقط اولین کندل معتبر)
    # ATR(5) رو از کندل‌های قبل از بریک‌اوت حساب می‌کنیم
    # برای سادگی از ATR کندل فعلی که تو df هست استفاده می‌کنیم
    for candle in potential_breakout_candles:
        # ATR(5) رو از ۵ کندل قبلی همین کندل حساب می‌کنیم
        candle_idx = closed[closed["datetime"] == candle["datetime"]].index[0]
        prev_5 = closed.loc[:candle_idx].tail(6).head(5)  # ۵ کندل قبل از کندل جاری
        if len(prev_5) < 5:
            continue
            
        # محاسبه True Range برای ۵ کندل
        tr_list = []
        for i in range(1, len(prev_5)):
            h = float(prev_5.iloc[i]["high"])
            l = float(prev_5.iloc[i]["low"])
            pc = float(prev_5.iloc[i-1]["close"])
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        atr_5 = sum(tr_list) / len(tr_list) if tr_list else 0.0
        
        if atr_5 <= 0:
            continue

        # مشخصات کندل
        candle_high = float(candle["high"])
        candle_low = float(candle["low"])
        candle_open = float(candle["open"])
        candle_close = float(candle["close"])
        
        body = abs(candle_close - candle_open)
        total_range = candle_high - candle_low
        
        if total_range <= 0:
            continue

        # شرط بدنه: حداقل ۶۰٪ از کل کندل
        body_ratio = body / total_range
        if body_ratio < 0.6:
            continue

        # شرط قدرت: بدنه بزرگتر از ATR(5) باشه
        if body < atr_5:
            continue

        # بررسی بریک‌اوت به بالا (BUY)
        if candle_close > range_high and candle_close > candle_open:
            # کندل باید کاملاً بیرون رنج بسته بشه
            # و کندل قبلی نباید بیرون رنج بسته شده باشه (چون فقط اولین کندل معتبره)
            # (چون potential_breakout_candles رو به ترتیب چک می‌کنیم، همین که به اینجا رسیدیم یعنی اولین کندل معتبره)
            
            return {
                "pattern": "ny_orb_breakout_buy",
                "strategy": "NY_BREAKOUT",
                "direction": "BUY",
                "range_high": round(range_high, 2),
                "range_low": round(range_low, 2),
                "sl_candle_low": round(candle_low, 2),
                "entry": round(candle_close, 2), # ورود در قیمت بسته شدن کندل تایید
                "candle_high": round(candle_high, 2),
            }

        # بررسی بریک‌اوت به پایین (SELL)
        if candle_close < range_low and candle_close < candle_open:
            return {
                "pattern": "ny_orb_breakout_sell",
                "strategy": "NY_BREAKOUT",
                "direction": "SELL",
                "range_high": round(range_high, 2),
                "range_low": round(range_low, 2),
                "sl_candle_high": round(candle_high, 2),
                "entry": round(candle_close, 2),
                "candle_low": round(candle_low, 2),
            }

    return None