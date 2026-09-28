"""
GoldPro V2 — Out-of-Sample Test
تست پایداری پارامترها روی داده‌ای که بهینه نشده
"""
import requests
import pandas as pd
import numpy as np

from src.config import TWELVEDATA_KEY, SYMBOL
from src.indicators import add_indicators
from src.strategy import detect_double_top_sell, detect_double_bottom_buy
from src.telegram_bot import send_telegram


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


def run_backtest(df, adx_min=15, sl_mult=2.5, tp_mult=1.5, max_bars_since=2):
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

        if adx_ < adx_min:
            i += 1
            continue

        sell_setup = detect_double_top_sell(rsi_series, max_bars_since_peak=max_bars_since)
        buy_setup = detect_double_bottom_buy(rsi_series, max_bars_since_trough=max_bars_since)

        signal = None
        if sell_setup:
            sl = round(price + sl_mult * atr_, 2)
            tp = round(price - tp_mult * atr_, 2)
            signal = {"side": "SELL", "entry": price, "sl": sl, "tp": tp, "idx": i}
        elif buy_setup:
            sl = round(price - sl_mult * atr_, 2)
            tp = round(price + tp_mult * atr_, 2)
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
    print("🔬 GoldPro V2 — Out-of-Sample Test")
    print("=" * 70)

    lines = ["🔬 <b>Out-of-Sample Test</b>\n"]
    lines.append("پارامترها: ADX=15, SL=2.5, TP=1.5\n")

    tf = "15min"
    df_full = fetch_history(tf, outputsize=5000)
    df_full = add_indicators(df_full)
    total = len(df_full)

    # تقسیم 60/40
    split_idx = int(total * 0.6)
    df_train = df_full.iloc[:split_idx].reset_index(drop=True)
    df_test = df_full.iloc[split_idx:].reset_index(drop=True)

    print(f"📊 Total candles: {total}")
    print(f"   Train: {len(df_train)} ({df_full['datetime'].iloc[0]} → {df_full['datetime'].iloc[split_idx-1]})")
    print(f"   Test:  {len(df_test)} ({df_full['datetime'].iloc[split_idx]} → {df_full['datetime'].iloc[-1]})\n")

    # تست روی TRAIN
    print("🧪 Testing on TRAIN (60%):")
    train_trades = run_backtest(df_train)
    train_stats = calc_stats(train_trades)
    if train_stats:
        print(f"   Trades={train_stats['total']} WR={train_stats['win_rate']}% PF={train_stats['pf']} PnL={train_stats['pnl']} DD={train_stats['max_dd']}")

    # تست روی TEST
    print("\n🧪 Testing on TEST (40%) — Out-of-Sample:")
    # برای TEST، باید اندیکاتورها از قبل محاسبه شدن (در df_test ادامه دارن)
    test_trades = run_backtest(df_test)
    test_stats = calc_stats(test_trades)
    if test_stats:
        print(f"   Trades={test_stats['total']} WR={test_stats['win_rate']}% PF={test_stats['pf']} PnL={test_stats['pnl']} DD={test_stats['max_dd']}")

    # گزارش تلگرام
    lines.append(f"📊 <b>داده کل:</b> {total} کندل")
    lines.append(f"🟢 Train: {len(df_train)}")
    lines.append(f"🔵 Test:  {len(df_test)}\n")

    if train_stats:
        lines.append("📈 <b>TRAIN (60%):</b>")
        lines.append(f"   Trades: {train_stats['total']}")
        lines.append(f"   WR: {train_stats['win_rate']}%")
        lines.append(f"   PF: <b>{train_stats['pf']}</b>")
        lines.append(f"   PnL: {train_stats['pnl']}")
        lines.append(f"   DD: {train_stats['max_dd']}")

    if test_stats:
        lines.append("\n📉 <b>TEST (40%, Out-of-Sample):</b>")
        lines.append(f"   Trades: {test_stats['total']}")
        lines.append(f"   WR: {test_stats['win_rate']}%")
        lines.append(f"   PF: <b>{test_stats['pf']}</b>")
        lines.append(f"   PnL: {test_stats['pnl']}")
        lines.append(f"   DD: {test_stats['max_dd']}")

    # قضاوت
    if train_stats and test_stats:
        pf_train = train_stats["pf"]
        pf_test = test_stats["pf"]
        diff_pct = abs(pf_train - pf_test) / pf_train * 100 if pf_train > 0 else 100

        lines.append(f"\n🎯 <b>تحلیل:</b>")
        if diff_pct < 20:
            verdict = "✅ پایدار — استراتژی قابل اعتماد"
        elif diff_pct < 40:
            verdict = "🟡 متوسط — هوشیار باش"
        else:
            verdict = "❌ ناپایدار — احتمال Overfit"

        lines.append(f"اختلاف PF: {diff_pct:.1f}%")
        lines.append(f"{verdict}")

    print("\n📨 Sending report...")
    send_telegram("\n".join(lines))
    print("✅ Done")


if __name__ == "__main__":
    main()