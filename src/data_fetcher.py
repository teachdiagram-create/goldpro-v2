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