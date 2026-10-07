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

    # اگه قیمت جدید گرفته شده، state رو ذخیره کن
    if state.get("current_price") is not None:
        state_changed = True
        print(f"💰 Price updated: {state['current_price']}")

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
                    try:
                        send_win_sms(trade)
                    except Exception as e:
                        print(f"⚠️ WIN SMS error: {e}")
                    state["last_win_notified"] = trade["closed_at"]
                    print(f"🔔 WIN notifications sent")

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
    else:
        print("⏸ No changes, nothing to save")