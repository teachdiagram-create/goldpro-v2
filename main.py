from src.config import TIMEFRAMES, USE_GIST
from src.data_fetcher import fetch_ohlc
from src.indicators import add_indicators
from src.signal_logic import evaluate_signal
from src.telegram_bot import send_telegram, format_message
from src.notifier import send_signal_ntfy, send_win_ntfy
from src.trade_tracker import update_open_trades, calculate_win_stats


if USE_GIST:
    from src.state_manager import load_state, save_state, should_send, mark_sent
else:
    def load_state(): return {"last_signals": {}, "history": []}
    def save_state(s): return True
    def should_send(sig, st): return True
    def mark_sent(sig, st): return st


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

    # Ntfy Push
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

    # ۱. آنالیز تایم‌فریم‌ها
    for tf in TIMEFRAMES:
        try:
            state, changed, df = process_timeframe(tf, state)
            dataframes[tf] = df
            if changed:
                state_changed = True
        except Exception as e:
            print(f"❌ {tf} error: {e}")

    # ۲. پیگیری معاملات باز
    if USE_GIST and dataframes:
        print(f"\n🔎 Checking open trades...")
        state, closed_count = update_open_trades(state, dataframes)
        if closed_count > 0:
            state_changed = True
            print(f"✅ {closed_count} trade(s) closed")

        # آمار
        stats = calculate_win_stats(state.get("history", []))
        print(f"\n📊 Stats: {stats['wins']}W / {stats['losses']}L | "
              f"WR={stats['win_rate']}% | PnL={stats['total_pnl']:+.2f} | "
              f"PF={stats['profit_factor']}")

    # ۳. ذخیره State
    if state_changed:
        if save_state(state):
            print("💾 State saved")
        else:
            print("❌ Failed to save state")


if __name__ == "__main__":
    main()