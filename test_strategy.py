from src.config import TIMEFRAMES
from src.data_fetcher import fetch_ohlc
from src.indicators import add_indicators
from src.strategy import detect_double_top_sell, detect_double_bottom_buy
from src.signal_logic import evaluate_signal
from src.telegram_bot import send_telegram


def main():
    print("=" * 60)
    print("🔬 GoldPro V2 — Strategy Diagnostic")
    print("=" * 60)

    lines = ["🔬 <b>GoldPro V2 — Diagnostic</b>"]

    for tf in TIMEFRAMES:
        print(f"\n{'─' * 60}")
        print(f"📊 Timeframe: {tf}")
        print(f"{'─' * 60}")

        try:
            df = fetch_ohlc(tf)
            df = add_indicators(df)

            rsi = df["rsi"].iloc[:-1]
            last_rsi = float(rsi.iloc[-1])

            print(f"آخرین 10 RSI: {rsi.tail(10).round(1).tolist()}")
            print(f"RSI فعلی: {last_rsi:.1f}")

            sell_setup = detect_double_top_sell(rsi)
            buy_setup = detect_double_bottom_buy(rsi)
            signal = evaluate_signal(df, timeframe=tf)

            lines.append(f"\n📊 <b>{tf}</b>")
            lines.append(f"RSI: {last_rsi:.1f}")
            lines.append(f"SELL setup: {'✅' if sell_setup else '❌'}")
            lines.append(f"BUY setup: {'✅' if buy_setup else '❌'}")
            lines.append(f"Signal: {signal['side'] if signal else 'NO'}")

            print(f"SELL setup: {sell_setup}")
            print(f"BUY setup: {buy_setup}")
            print(f"Signal: {signal}")

        except Exception as e:
            print(f"❌ Error in {tf}: {e}")
            lines.append(f"\n📊 <b>{tf}</b>\n❌ Error: {e}")

    print("\n📨 Sending diagnostic report to Telegram...")
    ok = send_telegram("\n".join(lines))
    print(f"📨 Send result: {ok}")
    print("✅ Done")


if __name__ == "__main__":
    main()