"""
Trade Tracker — پیگیری نتایج معاملات باز
بعد از هر سیگنال، چک می‌کنه کی TP یا SL می‌خوره
"""
from datetime import datetime


def check_trade_result(trade: dict, df) -> dict:
    """
    یه معامله باز رو با داده جدید چک می‌کنه
    اگه TP یا SL خورده باشه، نتیجه رو برمی‌گردونه
    """
    if trade.get("result"):
        # قبلاً بسته شده
        return trade

    side = trade["side"]
    entry = trade.get("entry")
    sl = trade.get("sl")
    tp = trade.get("tp")
    sent_at = trade.get("sent_at")

    if not all([entry, sl, tp, sent_at]):
        return trade

    # فقط کندل‌هایی که بعد از سیگنال اومدن
    signal_time = sent_at.replace("T", " ").split(".")[0]
    df["datetime_str"] = df["datetime"].astype(str)
    new_candles = df[df["datetime_str"] > signal_time]

    if len(new_candles) == 0:
        return trade

    # چک کردن هر کندل جدید
    for _, candle in new_candles.iterrows():
        high = float(candle["high"])
        low = float(candle["low"])

        if side == "BUY":
            # BUY: TP بالا، SL پایین
            if high >= tp:
                pnl = tp - entry
                return {
                    **trade,
                    "result": "WIN",
                    "exit_price": round(tp, 2),
                    "exit_time": str(candle["datetime"]),
                    "pnl": round(pnl, 2),
                    "closed_at": datetime.utcnow().isoformat(),
                }
            if low <= sl:
                pnl = entry - sl
                return {
                    **trade,
                    "result": "LOSS",
                    "exit_price": round(sl, 2),
                    "exit_time": str(candle["datetime"]),
                    "pnl": round(pnl, 2),
                    "closed_at": datetime.utcnow().isoformat(),
                }

        else:  # SELL
            # SELL: TP پایین، SL بالا
            if low <= tp:
                pnl = entry - tp
                return {
                    **trade,
                    "result": "WIN",
                    "exit_price": round(tp, 2),
                    "exit_time": str(candle["datetime"]),
                    "pnl": round(pnl, 2),
                    "closed_at": datetime.utcnow().isoformat(),
                }
            if high >= sl:
                pnl = sl - entry
                return {
                    **trade,
                    "result": "LOSS",
                    "exit_price": round(sl, 2),
                    "exit_time": str(candle["datetime"]),
                    "pnl": round(pnl, 2),
                    "closed_at": datetime.utcnow().isoformat(),
                }

    # هنوز باز
    return trade


def update_open_trades(state: dict, dataframes: dict) -> tuple:
    """
    همه معاملات باز رو چک می‌کنه و آپدیت می‌کنه
    
    dataframes: dict with {"5min": df5, "15min": df15}
    Returns: (updated_state, changed_count)
    """
    history = state.get("history", [])
    if not history:
        return state, 0

    updated_count = 0
    new_history = []

    for trade in history:
        if trade.get("result"):
            # قبلاً بسته شده
            new_history.append(trade)
            continue

        # چک کن کدوم تایم‌فریم
        tf = trade.get("timeframe", "5min")
        df = dataframes.get(tf)

        if df is None or len(df) == 0:
            new_history.append(trade)
            continue

        updated_trade = check_trade_result(trade, df)

        if updated_trade.get("result") and not trade.get("result"):
            # تغییر کرد → نتیجه جدید
            updated_count += 1
            emoji = "✅" if updated_trade["result"] == "WIN" else "❌"
            print(f"  {emoji} Trade closed: {tf} {trade['side']} "
                  f"→ {updated_trade['result']} "
                  f"({updated_trade['pnl']:+.2f})")

        new_history.append(updated_trade)

    state["history"] = new_history
    return state, updated_count


def calculate_win_stats(history: list) -> dict:
    """محاسبه آمار برد/باخت"""
    closed = [t for t in history if t.get("result")]
    wins = [t for t in closed if t["result"] == "WIN"]
    losses = [t for t in closed if t["result"] == "LOSS"]

    total_pnl = sum(t.get("pnl", 0) for t in closed)
    total_win_pnl = sum(t.get("pnl", 0) for t in wins)
    total_loss_pnl = abs(sum(t.get("pnl", 0) for t in losses))

    win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0

    return {
        "open": len([t for t in history if not t.get("result")]),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(total_win_pnl / len(wins), 2) if wins else 0,
        "avg_loss": round(total_loss_pnl / len(losses), 2) if losses else 0,
        "profit_factor": round(total_win_pnl / total_loss_pnl, 2) if total_loss_pnl > 0 else 0,
    }