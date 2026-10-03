"""
GoldPro V2 — Backtest روی Timeframe 1H
"""
import requests
import pandas as pd
from src.config import TWELVEDATA_KEY, SYMBOL
from src.indicators import add_indicators
from src.strategy import detect_double_top_sell, detect_double_bottom_buy
from src.telegram_bot import send_telegram


ADX_MIN = 15
SL_MULT = 2.5
TP_MULT = 1.5
MAX_BARS_SINCE = 2


def fetch_history(timeframe: str, outputsize: int = 5000) -> pd.DataFrame:
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": timeframe,
        "outputsize": outputsize,
        "apikey": TWELVEDATA_KEY,
        "format": "JSON",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "values" not in data:
        raise RuntimeError(f"TwelveData error: {data}")
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    return df


def simulate_trade(df, entry_idx, side, sl, tp, entry_price, max_bars=200):
    for i in range(entry_idx + 1, min(entry_idx + max_bars, len(df))):
        bar = df.iloc[i]
        high, low = float(bar["high"]), float(bar["low"])
        if side == "BUY":
            if low <= sl:
                return "LOSS", sl - entry_price, i
            if high >= tp:
                return "WIN", tp - entry_price, i
        else:
            if high >= sl:
                return "LOSS", entry_price - sl, i
            if low <= tp:
                return "WIN", entry_price - tp, i
    last = df.iloc[min(entry_idx + max_bars, len(df) - 1)]
    exit_price = float(last["close"])
    pnl = (exit_price - entry_price) if side == "BUY" else (entry_price - exit_price)
    return "TIMEOUT", pnl, entry_idx + max_bars


def run_backtest(df):
    trades = []
    start_idx = 100
    end_idx = len(df) - 100
    i = start_idx
    while i < end_idx:
        window = df.iloc[:i + 1]
        current = window.iloc[-1]
        rsi_series = window["rsi"].iloc[:-1]
        price = float(current["close"])
        atr_ = float(current["atr"])
        adx_ = float(current["adx"])
        if pd.isna(atr_) or atr_ <= 0 or pd.isna(adx_):
            i += 1
            continue
        if adx_ < ADX_MIN:
            i += 1
            continue
        sell_setup = detect_double_top_sell(rsi_series, max_bars_since_peak=MAX_BARS_SINCE)
        buy_setup = detect_double_bottom_buy(rsi_series, max_bars_since_trough=MAX_BARS_SINCE)
        signal = None
        if sell_setup:
            sl = round(price + SL_MULT * atr_, 2)
            tp = round(price - TP_MULT * atr_, 2)
            signal = {"side": "SELL", "entry": price, "sl": sl, "tp": tp, "idx": i}
        elif buy_setup:
            sl = round(price - SL_MULT * atr_, 2)
            tp = round(price + TP_MULT * atr_, 2)
            signal = {"side": "BUY", "entry": price, "sl": sl, "tp": tp, "idx": i}
        if signal:
            result, pnl, exit_idx = simulate_trade(
                df, i, signal["side"], signal["sl"], signal["tp"], signal["entry"]
            )
            trades.append({"result": result, "pnl": pnl})
            i = exit_idx + 1
        else:
            i += 1
    return trades


def calc_stats(trades):
    if not trades:
        return None
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    total_win = sum(t["pnl"] for t in wins)
    total_loss = abs(sum(t["pnl"] for t in losses))
    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t["pnl"])
    peak = equity[0]
    max_dd = 0
    for v in equity:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)
    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "pnl": round(sum(t["pnl"] for t in trades), 2),
        "pf": round(total_win / total_loss, 2) if total_loss > 0 else 999,
        "max_dd": round(max_dd, 2),
    }


def main():
    print("=" * 70)
    print("🔬 GoldPro V2 — Backtest 1H")
    print("=" * 70)

    lines = ["🔬 <b>Backtest 1H</b>\n"]

    tf = "1h"
    df = fetch_history(tf, outputsize=5000)
    df = add_indicators(df)
    print(f"📥 Got {len(df)} candles ({df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]})\n")

    trades = run_backtest(df)
    stats = calc_stats(trades)

    if stats:
        print(f"📊 Results:")
        print(f"  Trades: {stats['total']}")
        print(f"  Wins: {stats['wins']}")
        print(f"  Losses: {stats['losses']}")
        print(f"  Win Rate: {stats['win_rate']}%")
        print(f"  PnL: {stats['pnl']}")
        print(f"  PF: {stats['pf']}")
        print(f"  Max DD: {stats['max_dd']}")

        lines.append(f"📥 کندل‌ها: {len(df)}")
        lines.append(f"🎯 معاملات: {stats['total']}")
        lines.append(f"✅ برد: {stats['wins']} | ❌ باخت: {stats['losses']}")
        lines.append(f"💯 Win Rate: <b>{stats['win_rate']}%</b>")
        lines.append(f"💰 PnL: {stats['pnl']}")
        lines.append(f"📊 PF: <b>{stats['pf']}</b>")
        lines.append(f"📉 Max DD: {stats['max_dd']}")
    else:
        print("⚠️ No trades found")
        lines.append("⚠️ هیچ معامله‌ای ثبت نشد")

    print("\n📨 Sending to Telegram...")
    send_telegram("\n".join(lines))
    print("✅ Done")


if __name__ == "__main__":
    main()