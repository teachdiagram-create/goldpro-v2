"""
Trade Tracker — پیگیری نتایج معاملات باز
"""
from datetime import datetime
import pandas as pd


def check_trade_result(trade: dict, df) -> dict:
    """
    یه معامله باز رو با داده جدید چک می‌کنه.
    اگه TP یا SL خورده باشه، نتیجه رو برمی‌گردونه.
    """
    if trade.get("result"):
        return trade

    side = trade["side"]
    entry = trade.get("entry")
    sl = trade.get("sl")
    tp = trade.get("tp")
    sent_at = trade.get("sent_at")

    if not all([entry, sl, tp, sent_at]):
        return trade

    try:
        # ۱. زمان سیگنال رو به datetime تبدیل می‌کنیم
        signal_dt = datetime.fromisoformat(sent_at)
        if signal_dt.tzinfo is None:
            signal_dt = signal_dt.replace(tzinfo=pd.Timestamp.now().tz)
    except Exception:
        return trade

    # ۲. آماده‌سازی دیتافریم و چک کردن کندل‌های جدید
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["datetime"]):
        df["datetime"] = pd.to_datetime(df["datetime"])
    
    if df["datetime"].dt.tz is None:
        df["datetime"] = df["datetime"].dt.tz_localize(signal_dt.tzinfo)
        
    # فقط کندل‌هایی که بعد از سیگنال اومدن
    new_candles = df[df["datetime"] > signal_dt]

    if len(new_candles) == 0:
        return trade

    for _, candle in new_candles.iterrows():
        high = float(candle["high"])
        low = float(candle["low"])
        close = float(candle["close"])
        open_price = float(candle["open"])
        candle_dt = str(candle["datetime"])

        # ─── بررسی گپ قیمت (Gap) ───
        # اگه قیمت باز شدن کندل از SL یا TP رد شده باشه (گپ)
        if side == "BUY":
            if open_price <= sl:
                # گپ نزولی: SL با قیمت باز شدن پر می‌شه، نه قیمت دقیق SL
                pnl = open_price - entry
                return {**trade, "result": "LOSS", "exit_price": round(open_price, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
            if open_price >= tp:
                pnl = open_price - entry
                return {**trade, "result": "WIN", "exit_price": round(open_price, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
        else:  # SELL
            if open_price >= sl:
                pnl = entry - open_price
                return {**trade, "result": "LOSS", "exit_price": round(open_price, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
            if open_price <= tp:
                pnl = entry - open_price
                return {**trade, "result": "WIN", "exit_price": round(open_price, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}

        # ─── بررسی برخورد TP و SL در کندل ───
        if side == "BUY":
            if low <= sl and high >= tp:
                # 🚨 هر دو تو یه کندل لمس شدن
                # تشخیص اینکه کدوم اول زده شده بر اساس فاصله از Open
                if abs(open_price - sl) < abs(tp - open_price):
                    # SL به Open نزدیک‌تره، پس اول SL زده شده
                    pnl = sl - entry
                    return {**trade, "result": "LOSS", "exit_price": round(sl, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
                else:
                    pnl = tp - entry
                    return {**trade, "result": "WIN", "exit_price": round(tp, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
            
            if low <= sl:
                pnl = sl - entry
                return {**trade, "result": "LOSS", "exit_price": round(sl, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
            
            if high >= tp:
                pnl = tp - entry
                return {**trade, "result": "WIN", "exit_price": round(tp, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}

        else:  # SELL
            if high >= sl and low <= tp:
                if abs(open_price - sl) < abs(tp - open_price):
                    pnl = entry - sl
                    return {**trade, "result": "LOSS", "exit_price": round(sl, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
                else:
                    pnl = entry - tp
                    return {**trade, "result": "WIN", "exit_price": round(tp, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}

            if high >= sl:
                pnl = entry - sl
                return {**trade, "result": "LOSS", "exit_price": round(sl, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
                
            if low <= tp:
                pnl = entry - tp
                return {**trade, "result": "WIN", "exit_price": round(tp, 2), "exit_time": candle_dt, "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}

    return trade