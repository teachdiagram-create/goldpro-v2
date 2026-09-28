"""
GoldPro V2 — Grid Search Optimization
بهینه‌سازی پارامترهای استراتژی روی داده تاریخی
"""
import itertools
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
        high = float(bar["high"])
        low = float(bar["low"])

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


def run_backtest(df, adx_min, sl_mult, tp_mult, max_bars_since=2):
    """
    اجرای بک‌تست با پارامترهای مشخص
    نیاز داره که max_bars_since_peak رو به strategy پاس بدیم
    """
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

        # فیلتر ADX
        if adx_ < adx_min:
            i += 1
            continue

        # چک دابل تاپ/باتم
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
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "pnl": round(sum(t["pnl"] for t in trades), 2),
        "pf": round(total_win / total_loss, 2) if total_loss > 0 else 999,
        "max_dd": round(max_dd, 2),
    }


def main():
    print("=" * 70)
    print("🔬 GoldPro V2 — Grid Search Optimization")
    print("=" * 70)

    lines = ["🔬 <b>Grid Search Results</b>\n"]

    # فقط M15 — چون M5 ضعیفه
    tf = "15min"
    print(f"\n📊 Fetching {tf} data...")
    df = fetch_history(tf, outputsize=5000)
    df = add_indicators(df)
    print(f"📥 Got {len(df)} candles\n")

    # پارامترها
    adx_values = [10, 15, 20]
    sl_values = [2.0, 2.5, 3.0]
    tp_values = [1.5, 2.0, 2.5, 3.0]

    results = []
    total_combos = len(adx_values) * len(sl_values) * len(tp_values)
    print(f"🔄 Testing {total_combos} combinations...\n")

    for idx, (adx, sl_m, tp_m) in enumerate(
        itertools.product(adx_values, sl_values, tp_values), 1
    ):
        trades = run_backtest(df, adx, sl_m, tp_m)
        stats = calc_stats(trades)
        if stats and stats["total"] >= 10:
            stats["adx"] = adx
            stats["sl"] = sl_m
            stats["tp"] = tp_m
            results.append(stats)
            print(
                f"  [{idx}/{total_combos}] ADX={adx} SL={sl_m} TP={tp_m} → "
                f"Trades={stats['total']} WR={stats['win_rate']}% PF={stats['pf']} DD={stats['max_dd']}"
            )

    # مرتب‌سازی بر اساس PF
    results.sort(key=lambda x: (x["pf"], x["pnl"]), reverse=True)

    print("\n" + "=" * 70)
    print("🏆 TOP 5 COMBINATIONS (by Profit Factor)")
    print("=" * 70)
    lines.append(f"📊 <b>{tf}</b>\n")
    lines.append("🏆 <b>Top 5:</b>")

    for i, r in enumerate(results[:5], 1):
        line = (
            f"\n{i}. ADX={r['adx']} SL={r['sl']}×ATR TP={r['tp']}×ATR\n"
            f"   Trades: {r['total']} | WR: {r['win_rate']}% | PF: <b>{r['pf']}</b>\n"
            f"   PnL: {r['pnl']} | Max DD: {r['max_dd']}"
        )
        print(line)
        lines.append(line)

    # بهترین ترکیب
    if results:
        best = results[0]
        print(f"\n🥇 بهترین ترکیب:")
        print(f"   ADX_MIN = {best['adx']}")
        print(f"   SL_ATR_MULT = {best['sl']}")
        print(f"   TP_ATR_MULT = {best['tp']}")
        print(f"\n   Win Rate: {best['win_rate']}%")
        print(f"   Profit Factor: {best['pf']}")
        print(f"   Total PnL: {best['pnl']}")
        print(f"   Max DD: {best['max_dd']}")

        lines.append(f"\n\n🥇 <b>بهترین:</b>")
        lines.append(f"ADX_MIN = {best['adx']}")
        lines.append(f"SL_ATR_MULT = {best['sl']}")
        lines.append(f"TP_ATR_MULT = {best['tp']}")
        lines.append(f"WR: {best['win_rate']}% | PF: <b>{best['pf']}</b>")

    print("\n📨 Sending to Telegram...")
    send_telegram("\n".join(lines))
    print("✅ Done")


if __name__ == "__main__":
    main()