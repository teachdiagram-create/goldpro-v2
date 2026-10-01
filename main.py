from src.config import TIMEFRAMES, USE_GIST
from src.data_fetcher import fetch_ohlc
from src.indicators import add_indicators
from src.signal_logic import evaluate_signal
from src.telegram_bot import send_telegram, format_message
from src.notifier import send_signal_ntfy, send_win_ntfy


if USE_GIST:
    from src.state_manager import load_state, save_state, should_send, mark_sent
    from src.trade_tracker import update_open_trades, calculate_win_stats
else:
    def load_state():
        return {"last_signals": {}, "history": []}

    def save_state(state):
        return True

    def should_send(signal, state):
        return True

    def mark_sent(signal, state):
        return state

    def update_open_trades(state, dataframes):
        return state, 0

    def calculate_win_stats(history):
        return {}


def process_timeframe(tf, state):
    print(f"\n🔍 Analyzing {tf}...")

    df = fetch_ohlc(tf)
    df = add_indicators(df)

    signal = evaluate_signal(df, timeframe=tf)

    if signal is None:
        print(f"⏸ {tf}: NO SIGNAL")
        return state, False, df

    print(f"✅ {tf}: {signal['side']} @ {signal['entry']}")

    if not should_send(signal, state):
        print(f"⏸ {tf}: Cooldown active, skipped")
        return state, False, df

    ok = send_telegram(format_message(signal))
    if ok:
        state = mark_sent(signal, state)
        print(f"📨 {tf}: Telegram sent")

        if send_signal_ntfy(signal):
            print(f"🔔 {tf}: Ntfy sent")
        else:
            print(f"⚠️ {tf}: Ntfy failed")

        return state, True, df
    else:
        print(f"❌ {tf}: Telegram failed")
        return state, False, df


def main():
    print("▶ GoldPro V2 started")

    state = load_state()
    print(f"📦 State keys: {list(state.keys())}")

    state_changed = False
    dataframes = {}

    for tf in TIMEFRAMES:
        try:
            state, changed, df = process_timeframe(tf, state)
            dataframes[tf] = df
            if changed:
                state_changed = True
        except Exception as e:
            print(f"❌ {tf} error: {e}")

    if USE_GIST and dataframes:
        print(f"\n🔎 Checking open trades...")
        state, closed_count = update_open_trades(state, dataframes)
        if closed_count > 0:
            state_changed = True
            print(f"✅ {closed_count} trade(s) closed")

            for trade in state.get("history", []):
                if (trade.get("result") == "WIN"
                        and trade.get("closed_at")
                        and trade.get("closed_at") > state.get("last_win_notified", "1970-01-01")):
                    send_win_ntfy(trade)
                    state["last_win_notified"] = trade["closed_at"]
                    print(f"🔔 WIN notification sent")

        stats = calculate_win_stats(state.get("history", []))
        if stats:
            print(f"\n📊 Stats: {stats.get('wins', 0)}W / {stats.get('losses', 0)}L | "
                  f"WR={stats.get('win_rate', 0)}% | "
                  f"PnL={stats.get('total_pnl', 0):+.2f} | "
                  f"PF={stats.get('profit_factor', 0)}")

    if state_changed:
        if save_state(state):
            print("💾 State saved")
        else:
            print("❌ Failed to save state")


if __name__ == "__main__":
    main()