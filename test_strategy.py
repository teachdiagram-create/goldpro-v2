from src.data_fetcher import fetch_ohlc
from src.indicators import add_indicators
from src.strategy import detect_double_top_sell, detect_double_bottom_buy

for tf in ["5min", "15min"]:
    print(f"\n{'='*50}")
    print(f"Timeframe: {tf}")
    print('='*50)

    df = fetch_ohlc(tf)
    df = add_indicators(df)

    rsi = df["rsi"].iloc[:-1]

    print(f"RSI آخرین 10 کندل: {rsi.tail(10).round(1).tolist()}")

    sell = detect_double_top_sell(rsi)
    buy = detect_double_bottom_buy(rsi)

    print(f"SELL setup: {sell}")
    print(f"BUY  setup: {buy}")
