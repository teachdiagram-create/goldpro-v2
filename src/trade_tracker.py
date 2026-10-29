"""
Trade Tracker — پیگیری نتایج معاملات باز
"""
from datetime import datetime
import pandas as pd


def check_trade_result(trade: dict, df) -> dict:
    """
    یه معامله باز رو با داده جدید چک می‌کنه.
    اگه TP یا SL خورده باشه، نتیجه رو برمی‌گردونه.
    """
    if trade.get("result"):
        return trade

    side = trade["side"]
    entry = trade.get("entry")
    sl = trade.get("sl")
    tp = trade.get("tp")
    sent_at = trade.get("sent_at")

    if not all([entry, sl, tp, sent_at]):
        return trade

    try:
        # ۱. زمان سیگنال رو به datetime تبدیل می‌کنیم
        signal_dt = datetime.fromisoformat(sent_at)
        if signal_dt.tzinfo is None:
            signal_dt = signal_dt.replace(tzinfo=pd.Timestamp.now().tz)
    except Exception:
        return trade

    # ۲. آماده‌سازی دیتافریم و چک کردن کندل‌های جدید
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["datetime"]):
        df["datetime"] = pd.to_datetime(df["datetime"])
    
    # اگه تایم‌زون نداره، اضافه می‌کنیم که با سیگنال هماهنگ شه
    if df["datetime"].dt.tz is None:
        df["datetime"] = df["datetime"].dt.tz_localize(signal_dt.tzinfo)
        
    # فقط کندل‌هایی که بعد از سیگنال اومدن
    new_candles = df[df["datetime"] > signal_dt]

    if len(new_candles) == 0:
        return trade

    for _, candle in new_candles.iterrows():
        high = float(candle["high"])
        low = float(candle["low"])

        if side == "BUY":
            if high >= tp:
                pnl = tp - entry
                return {**trade, "result": "WIN", "exit_price": round(tp, 2), "exit_time": str(candle["datetime"]), "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
            if low <= sl:
                pnl = sl - entry
                return {**trade, "result": "LOSS", "exit_price": round(sl, 2), "exit_time": str(candle["datetime"]), "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
        else:  # SELL
            if low <= tp:
                pnl = entry - tp
                return {**trade, "result": "WIN", "exit_price": round(tp, 2), "exit_time": str(candle["datetime"]), "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}
            if high >= sl:
                pnl = entry - sl
                return {**trade, "result": "LOSS", "exit_price": round(sl, 2), "exit_time": str(candle["datetime"]), "pnl": round(pnl, 2), "closed_at": datetime.utcnow().isoformat()}

    return trade


def _find_df(dataframes: dict, symbol: str, timeframe: str):
    key_new = f"{symbol}:{timeframe}"
    if key_new in dataframes:
        return dataframes[key_new]
    if timeframe in dataframes:
        return dataframes[timeframe]
    for k, v in dataframes.items():
        if k.endswith(f":{timeframe}") or k == timeframe:
            return v
    return None


def update_open_trades(state: dict, dataframes: dict) -> tuple:
    history = state.get("history", [])
    if not history:
        return state, 0

    updated_count = 0
    new_history = []

    for trade in history:
        if trade.get("result"):
            new_history.append(trade)
            continue

        tf = trade.get("timeframe", "5min")
        symbol = trade.get("symbol", "XAU/USD")
        df = _find_df(dataframes, symbol, tf)

        if df is None or len(df) == 0:
            print(f"  ⚠️ No df for {symbol} {tf} - keeping open")
            new_history.append(trade)
            continue

        updated_trade = check_trade_result(trade, df)

        if updated_trade.get("result") and not trade.get("result"):
            updated_count += 1
            emoji = "✅" if updated_trade["result"] == "WIN" else "❌"
            print(f"  {emoji} Trade closed: {symbol} {tf} {trade['side']} -> {updated_trade['result']} ({updated_trade['pnl']:+.2f})")

        new_history.append(updated_trade)

    state["history"] = new_history
    return state, updated_count


def calculate_win_stats(history: list) -> dict:
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