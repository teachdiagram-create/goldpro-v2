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


def fetch_dxy_yfinance(timeframe: str = "5min") -> pd.DataFrame:
    """
    دریافت DXY از yfinance و تبدیل دقیق به UTC.
    """
    import yfinance as yf
    
    interval_map = {
        "5min": "5m",
        "15min": "15m",
        "1h": "60m",
        "1d": "1d",
    }
    interval = interval_map.get(timeframe, "5m")
    
    try:
        ticker = yf.Ticker("DX-Y.NYB")
        df = ticker.history(period="1d", interval=interval)
        
        if df.empty:
            print(f"⚠️ yfinance DXY returned empty for {timeframe}")
            return None
        
        df = df.reset_index()
        df = df.rename(columns={
            "Datetime": "datetime",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
        })
        
        # 🚨 اصلاح: قبل از حذف tz، به UTC تبدیل می‌کنیم
        if df["datetime"].dt.tz is not None:
            df["datetime"] = df["datetime"].dt.tz_convert("UTC").dt.tz_localize(None)
        else:
            # اگه tz نداره، فرض می‌کنیم UTC هست
            pass
        
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        
        df = df[["datetime", "open", "high", "low", "close"]]
        df = df.sort_values("datetime").reset_index(drop=True)
        
        print(f"✅ DXY (yfinance) fetched: {len(df)} candles")
        return df
        
    except Exception as e:
        print(f"⚠️ yfinance DXY fetch failed: {e}")
        return None