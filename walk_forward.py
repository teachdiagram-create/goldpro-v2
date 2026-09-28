"""
GoldPro V2 — Walk-Forward Test
تست استراتژی روی ۵ بازه تاریخی مختلف
"""
import requests
import pandas as pd
import numpy as np

from src.config import TWELVEDATA_KEY, SYMBOL
from src.indicators import add_indicators
from src.strategy import detect_double_top_sell, detect_double_bottom_buy
from src.telegram_bot import send_telegram


# پارامترهای بهینه‌شده
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

    if end_idx <= start_idx:
        return trades

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
    print("🔬 GoldPro V2 — Walk-Forward Test")
    print("=" * 70)
    print(f"پارامترها: ADX={ADX_MIN}, SL={SL_MULT}, TP={TP_MULT}\n")

    lines = ["🔬 <b>Walk-Forward Test</b>\n"]
    lines.append(f"پارامترها: ADX={ADX_MIN}, SL={SL_MULT}, TP={TP_MULT}\n")

    # داده کامل
    tf = "15min"
    df_full = fetch_history(tf, outputsize=5000)
    df_full = add_indicators(df_full)
    total = len(df_full)
    print(f"📊 Total candles: {total}\n")

    # ۵ تا split مختلف
    splits = [
        ("50/50", 0.50),
        ("60/40", 0.60),
        ("70/30", 0.70),
        ("40/60", 0.40),
        ("80/20", 0.80),
    ]

    results = []

    for label, train_ratio in splits:
        split_idx = int(total * train_ratio)
        df_test = df_full.iloc[split_idx:].reset_index(drop=True)

        if len(df_test) < 200:
            print(f"⏸ Split {label}: داده کافی نیست")
            continue

        trades = run_backtest(df_test)
        stats = calc_stats(trades)

        if stats:
            results.append({
                "label": label,
                "train_pct": int(train_ratio * 100),
                "test_pct": int((1 - train_ratio) * 100),
                "test_bars": len(df_test),
                **stats,
            })

            print(f"📊 Split {label} (Test از کندل {split_idx}):")
            print(f"   Trades={stats['total']} WR={stats['win_rate']}% PF={stats['pf']} PnL={stats['pnl']} DD={stats['max_dd']}\n")

    # ارسال به تلگرام
    lines.append("📊 <b>نتایج روی 5 بازه مختلف:</b>\n")

    for r in results:
        lines.append(
            f"<b>Split {r['label']}</b> ({r['test_bars']} کندل تست)\n"
            f"   Trades: {r['total']}\n"
            f"   WR: {r['win_rate']}%\n"
            f"   PF: <b>{r['pf']}</b>\n"
            f"   PnL: {r['pnl']}\n"
            f"   DD: {r['max_dd']}\n"
        )

    # تحلیل پایداری
    if results:
        pfs = [r["pf"] for r in results if r["pf"] < 900]
        wrs = [r["win_rate"] for r in results if r["total"] > 0]
        pnls = [r["pnl"] for r in results]

        avg_pf = round(sum(pfs) / len(pfs), 2) if pfs else 0
        min_pf = round(min(pfs), 2) if pfs else 0
        max_pf = round(max(pfs), 2) if pfs else 0
        avg_wr = round(sum(wrs) / len(wrs), 1) if wrs else 0
        positive_splits = sum(1 for p in pnls if p > 0)

        lines.append("\n🎯 <b>تحلیل پایداری:</b>")
        lines.append(f"   میانگین PF: <b>{avg_pf}</b>")
        lines.append(f"   کمترین PF: {min_pf}")
        lines.append(f"   بیشترین PF: {max_pf}")
        lines.append(f"   میانگین WR: {avg_wr}%")
        lines.append(f"   سودده: {positive_splits}/{len(results)} split")

        # قضاوت نهایی
        if avg_pf >= 1.5 and positive_splits == len(results) and min_pf >= 1.2:
            verdict = "✅ <b>عالی — استراتژی بسیار پایدار</b>"
        elif avg_pf >= 1.2 and positive_splits >= len(results) * 0.8:
            verdict = "🟢 <b>خوب — قابل اعتماد</b>"
        elif avg_pf >= 1.0 and positive_splits >= len(results) * 0.6:
            verdict = "🟡 <b>متوسط — با احتیاط</b>"
        else:
            verdict = "❌ <b>ضعیف — ناپایدار</b>"

        lines.append(f"\n{verdict}")

        print(f"\n🎯 تحلیل نهایی:")
        print(f"   میانگین PF: {avg_pf}")
        print(f"   سودده: {positive_splits}/{len(results)} split")
        print(f"   قضاوت: {verdict}")

    print("\n📨 Sending to Telegram...")
    send_telegram("\n".join(lines))
    print("✅ Done")


if __name__ == "__main__":
    main()