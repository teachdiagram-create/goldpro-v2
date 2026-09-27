from src.data_fetcher import fetch_ohlc
from src.indicators import add_indicators
from src.signal_logic import evaluate_signal
from src.state_manager import load_state, save_state, should_send, mark_sent
from src.telegram_bot import send_telegram, format_message


def main():
    print("▶ GoldPro V2 started")

    df = fetch_ohlc()
    df = add_indicators(df)

    signal = evaluate_signal(df)

    if signal is None:
        print("⏸ NO SIGNAL — nothing sent")
        return

    print(f"✅ Signal detected: {signal['side']} @ {signal['entry']}")

    state = load_state()
    if not should_send(signal, state):
        print("⏸ Cooldown active — skipped")
        return

    ok = send_telegram(format_message(signal))
    if ok:
        state = mark_sent(signal, state)
        save_state(state)
        print("📨 Telegram message sent")
    else:
        print("❌ Failed to send Telegram message")


if __name__ == "__main__":
    main()
