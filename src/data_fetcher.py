import requests
import pandas as pd
from src.config import TWELVEDATA_KEY, SYMBOL, INTERVAL, OUTPUT_SIZE


def fetch_ohlc() -> pd.DataFrame:
    """دریافت کندل‌های XAU/USD از TwelveData"""
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": OUTPUT_SIZE,
        "apikey": TWELVEDATA_KEY,
        "format": "JSON",
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    if "values" not in data:
        raise RuntimeError(f"TwelveData error: {data}")

    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    return df
