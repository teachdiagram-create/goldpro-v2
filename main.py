from datetime import datetime
from src.config import TIMEFRAMES, USE_GIST, ALLOWED_GRADES, MAX_OPEN_TRADES
from src.data_fetcher import fetch_ohlc, fetch_dxy_yfinance
from src.indicators import add_indicators
from src.signal_logic import evaluate_signal
from src.telegram_bot import send_telegram, format_message, format_win_message, format_loss_message
from src.notifier import send_signal_ntfy, send_trade_closed_ntfy
from src.sms_sender import send_signal_sms, send_win_sms
from src.risk_manager import can_open_trade

if USE_GIST:
    from src.state_manager import load_state, save_state, should_send, mark_sent
    from src.trade_tracker import update_open_trades, calculate_win_stats
else:
    def load_state(): return {"last_signals": {}, "history": []}
    def save_state(state): return True
    def should_send(signal, state): return True
    def mark_sent(signal, state): return state
    def update_open_trades(state, dataframes): return state, 0
    def calculate_win_stats(history): return {}


def process_timeframes(state, dataframes):
    print(f"\n🔍 Analyzing Gold M5 & M15 + DXY (yfinance)...")

    try:
        df_m5 = fetch_ohlc("5min", symbol="XAU/USD")
        df_m5 = add_indicators(df_m5)
        df_m15 = fetch_ohlc("15min", symbol="XAU/USD")
        df_m15 = add_indicators(df_m15)
        
        dataframes["XAU/USD:5min"] = df_m5
        dataframes["XAU/USD:15min"] = df_m15

        if len(df_m5) > 1:
            last_close = float(df_m5.iloc[-1]["close"])
            state["current_price"] = last_close
            state["price_updated_at"] = datetime.utcnow().isoformat()
            print(f"💰 Current XAU/USD: {last_close:.2f} (from M5)")

    except Exception as e:
        print(f"❌ Gold fetch failed - {e}")
        return state, False

    df_dxy = None
    try:
        df_dxy = fetch_dxy_yfinance("5min")
        if df_dxy is not None and len(df_dxy) > 0:
            df_dxy = add_indicators(df_dxy)
            print(f"✅ DXY (yfinance) fetched: {len(df_dxy)} candles")
        else:
            print("⚠️ DXY fetch failed (empty) - Correlation disabled")
            df_dxy = None
    except Exception as e:
        print(f"⚠️ DXY fetch failed - Correlation disabled: {e}")
        df_dxy = None

    signal = evaluate_signal(df_m5, df_m15, df_dxy, df_dxy)

    if signal is None:
        print(f"⏸ NO SIGNAL (no valid pattern)")
        return state, False

    grade = signal["quality"]["grade"]
    score = signal["quality"]["score"]
    strategy = signal["strategy"]
    
    print(f"✅ SIGNAL: {strategy} {signal['side']} @ {signal['entry']} | Grade={grade} Score={score}")
    print(f"   ⏰ Time: {signal['time']} UTC")

    if grade not in ALLOWED_GRADES:
        print(f"🚫 Grade {grade} not in {ALLOWED_GRADES}, skipped")
        return state, False

    allowed, reason = can_open_trade(state, strategy, max_open=MAX_OPEN_TRADES)
    if not allowed:
        print(f"🚫 {reason} - skipped")
        return state, False

    if not should_send(signal, state):
        print(f"⏸ Cooldown active, skipped")
        return state, False

    ok = send_telegram(format_message(signal))
    if ok:
        state = mark_sent(signal, state)
        print(f"📨 Telegram sent")

        try:
            if send_signal_ntfy(signal):
                print(f"🔔 Ntfy sent")
        except Exception as e:
            print(f"⚠️ Ntfy error: {e}")

        try:
            if send_signal_sms(signal):
                print(f"📲 SMS sent")
        except Exception as e:
            print(f"⚠️ SMS error: {e}")

        return state, True
    else:
        print(f"❌ Telegram failed")
        return state, False


def main():
    print("▶ GoldPro V2 started")
    print(f"   Allowed grades: {ALLOWED_GRADES}")
    print(f"   Max open trades per strategy: {MAX_OPEN_TRADES}")

    state = load_state()
    print(f"📦 State keys: {list(state.keys())}")

    open_by_strat = {}
    for t in state.get("history", []):
        if t.get("result") is None:
            strat = t.get("strategy", "UNKNOWN")
            open_by_strat[strat] = open_by_strat.get(strat, 0) + 1
    
    if open_by_strat:
        print(f"📊 Open trades by strategy: {open_by_strat}")
    else:
        print(f"📊 Open trades: 0")

    state_changed = False
    dataframes = {}

    state, changed = process_timeframes(state, dataframes)
    if changed:
        state_changed = True

    if state.get("current_price") is not None:
        state_changed = True

if USE_GIST and dataframes:
    print(f"\n🔎 Checking open trades...")
    try:
        state, closed_count = update_open_trades(state, dataframes)
        if closed_count > 0:
            state_changed = True
            print(f"✅ {closed_count} trade(s) closed")

            last_notified = state.get("last_notified", "1970-01-01")
            for trade in state.get("history", []):
                if (trade.get("result") in ["WIN", "LOSS"]
                        and trade.get("closed_at")
                        and trade.get("closed_at") > last_notified):
                    
                    if trade["result"] == "WIN":
                        msg = format_win_message(trade)
                    else:
                        msg = format_loss_message(trade)
                    send_telegram(msg, with_dashboard_button=True)
                    
                    send_trade_closed_ntfy(trade)
                    
                    if trade["result"] == "WIN":
                        try:
                            send_win_sms(trade)
                        except Exception as e:
                            print(f"⚠️ WIN SMS error: {e}")
                    
                    # اینجا last_notified رو آپدیت می‌کنیم
                    state["last_notified"] = trade["closed_at"]
                        
                        state["last_win_notified"] = trade["closed_at"]

            stats = calculate_win_stats(state.get("history", []))
            if stats:
                print(f"\n📊 Stats: {stats.get('wins', 0)}W / {stats.get('losses', 0)}L | "
                      f"WR={stats.get('win_rate', 0)}% | "
                      f"PnL={stats.get('total_pnl', 0):+.2f} | "
                      f"PF={stats.get('profit_factor', 0)}")
        except Exception as e:
            print(f"❌ update_open_trades error: {e}")

    if state_changed:
        if save_state(state):
            print("💾 State saved ✅")
        else:
            print("❌ Failed to save state")
    else:
        print("⏸ No changes")


if __name__ == "__main__":
    main()