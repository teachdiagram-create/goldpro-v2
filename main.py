from src.config import TIMEFRAMES, USE_GIST
from src.data_fetcher import fetch_ohlc
from src.indicators import add_indicators
from src.signal_logic import evaluate_signal
from src.telegram_bot import send_telegram, format_message


if USE_GIST:
    from src.state_manager import load_state, save_state, should_send, mark_sent
else:
    def load_state():
        return {}

    def save_state(state):
        return True

    def should_send(signal, state):
        return True

    def mark_sent(signal, state):
        return state


def process_timeframe(tf, state):
    print(f"\n🔍 Analyzing {tf}...")

    df = fetch_ohlc(tf)
    df = add_indicators(df)

    signal = evaluate_signal(df, timeframe=tf)

    if signal is None:
        print(f"⏸ {tf}: NO SIGNAL")
        return state, False

    print(f"✅ {tf}: {signal['side']} @ {signal['entry']}")

    if not should_send(signal, state):
        print(f"⏸ {tf}: Cooldown active, skipped")
        return state, False

    ok = send_telegram(format_message(signal))
    if ok:
        state = mark_sent(signal, state)
        print(f"📨 {tf}: Telegram sent")
        return state, True
    else:
        print(f"❌ {tf}: Telegram failed")
        return state, False


def main():
    print("▶ GoldPro V2 started")

    state = load_state()
    print(f"📦 State keys: {list(state.keys())}")

    state_changed = False

    for tf in TIMEFRAMES:
        try:
            state, changed = process_timeframe(tf, state)
            if changed:
                state_changed = True
        except Exception as e:
            print(f"❌ {tf} error: {e}")

    if state_changed:
        if save_state(state):
            print("💾 State saved")
        else:
            print("❌ Failed to save state")


if __name__ == "__main__":
    main()