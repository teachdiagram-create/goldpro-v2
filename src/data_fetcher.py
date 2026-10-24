import requests
import pandas as pd
from src.config import TWELVEDATA_KEY, OUTPUT_SIZE


def fetch_ohlc(timeframe: str = "5min", symbol: str = "XAU/USD") -> pd.DataFrame:
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": timeframe,
        "outputsize": OUTPUT_SIZE,
        "apikey": TWELVEDATA_KEY,
        "format": "JSON",
        "timezone": "UTC",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "values" not in data:
        raise RuntimeError(f"TwelveData error for {symbol}: {data}")
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    return df
import pandas as pd
import requests

def fetch_dxy_stooq(timeframe: str = "5min") -> pd.DataFrame:
    """
    دریافت DXY از Stooq (رایگان و بدون کلید).
    فقط برای تایم‌فریم‌های 5min, 15min, 1h, 4h, 1d کار می‌کنه.
    """
    # Stooq از نماد `dx.f` برای فیوچرز دلار استفاده می‌کنه
    # و بازه‌های زمانی رو با i=5, i=15, i=60, i=240, i=d مشخص می‌کنه
    interval_map = {
        "5min": "5",
        "15min": "15",
        "1h": "60",
        "4h": "240",
        "1d": "d",
    }
    i = interval_map.get(timeframe, "5")
    
    url = f"https://stooq.com/q/d/l/?s=dx.f&i={i}"
    
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        
        if df.empty or "Date" not in df.columns:
            raise RuntimeError(f"Stooq returned empty data for {timeframe}")
        
        # ستون‌ها: Date, Open, High, Low, Close, Volume
        df["datetime"] = pd.to_datetime(df["Date"])
        df = df.sort_values("datetime").reset_index(drop=True)
        
        # تغییر نام ستون‌ها به استاندارد پروژه
        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
        
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        
        return df[["datetime", "open", "high", "low", "close"]]
    
    except Exception as e:
        print(f"⚠️ Stooq DXY fetch failed: {e}")
        return None