"""
GoldPro V2 - Grid Search Optimization (v4 with structure buffer)
"""
import itertools
import requests
import pandas as pd
import numpy as np

from src.config import (
    TWELVEDATA_KEY, SYMBOL,
    ATR_MIN_USD, ATR_MAX_USD,
    MIN_SL_USD, MIN_TP_USD,
    BLOCKED_HOURS_UTC,
)
from src.indicators import add_indicators
from src.strategy import detect_double_top_sell, detect_double_bottom_buy
from src.telegram_bot import send_telegram


# ══════════════════════════════════════════════════════════════
#  Data
# ══════════════════════════════════════════════════════════════
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


def is_blocked_hour(dt) -> bool:
    try:
        return dt.hour in BLOCKED_HOURS_UTC
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
#  SL/TP (parameterized)
# ══════════════════════════════════════════════════════════════
def compute_sl_tp_v4(side, price, atr, adx_value,
                     recent_high=None, recent_low=None,
                     sl_base_mult=1.5, tp_mult=2.5,
                     adx_threshold=40, adx_boost=1.2,
                     sl_structure_buffer=0.2):
    if atr is None or atr <= 0 or price <= 0:
        return None, None, None, None, None

    if adx_value is not None and adx_value > adx_threshold:
        sl_mult = sl_base_mult * adx_boost
    else:
        sl_mult = sl_base_mult

    if side == "SELL":
        sl_structure = (recent_high + sl_structure_buffer * atr
                        if recent_high else price + MIN_SL_USD)
        sl_atr = price + sl_mult * atr
        sl = max(sl_structure, sl_atr)
        if (sl - price) < MIN_SL_USD:
            sl = price + MIN_SL_USD
        sl_dist = sl - price
    elif side == "BUY":
        sl_structure = (recent_low - sl_structure_buffer * atr
                        if recent_low else price - MIN_SL_USD)
        sl_atr = price - sl_mult * atr
        sl = min(sl_structure, sl_atr)
        if (price - sl) < MIN_SL_USD:
            sl = price - MIN_SL_USD
        sl_dist = price - sl
    else:
        return None, None, None, None, None

    tp_dist = max(tp_mult * atr, MIN_TP_USD)
    tp = price + tp_dist if side == "BUY" else price - tp_dist

    rr = tp_dist / sl_dist if sl_dist > 0 else 0
    return sl, tp, sl_dist, tp_dist, rr


# ══════════════════════════════════════════════════════════════
#  Simulate
# ══════════════════════════════════════════════════════════════
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


def run_backtest(df, adx_min, sl_mult, tp_mult,
                 adx_threshold=40, adx_boost=1.2,
                 sl_structure_buffer=0.2,
                 max_bars_since=2,
                 atr_min=ATR_MIN_USD, atr_max=ATR_MAX_USD,
                 block_hours=None):
    if block_hours is None:
        block_hours = BLOCKED_HOURS_UTC

    trades = []
    start_idx = 100
    end_idx = len(df) - 100
    i = start_idx

    while i < end_idx:
        window = df.iloc[:i + 1]
        current = window.iloc[-1]

        price = float(current["close"])
        atr_raw = float(current["atr"])
        adx_ = float(current["adx"])

        if pd.isna(atr_raw) or atr_raw <= 0 or pd.isna(adx_):
            i += 1
            continue
        if atr_raw < atr_min:
            i += 1
            continue
        atr_ = min(atr_raw, atr_max)
        if adx_ < adx_min:
            i += 1
            continue
        if is_blocked_hour(current["datetime"]):
            i += 1
            continue

        rsi_series = window["rsi"].iloc[:-1]
        sell_setup = detect_double_top_sell(rsi_series, max_bars_since_peak=max_bars_since)
        buy_setup = detect_double_bottom_buy(rsi_series, max_bars_since_trough=max_bars_since)

        signal = None
        if sell_setup:
            recent_high = float(window["high"].tail(20).max())
            sl, tp, sd, td, rr = compute_sl_tp_v4(
                "SELL", price, atr_, adx_,
                recent_high=recent_high,
                sl_base_mult=sl_mult, tp_mult=tp_mult,
                adx_threshold=adx_threshold, adx_boost=adx_boost,
                sl_structure_buffer=sl_structure_buffer,
            )
            if sl is not None:
                signal = {"side": "SELL", "entry": price, "sl": sl, "tp": tp, "idx": i}
        elif buy_setup:
            recent_low = float(window["low"].tail(20).min())
            sl, tp, sd, td, rr = compute_sl_tp_v4(
                "BUY", price, atr_, adx_,
                recent_low=recent_low,
                sl_base_mult=sl_mult, tp_mult=tp_mult,
                adx_threshold=adx_threshold, adx_boost=adx_boost,
                sl_structure_buffer=sl_structure_buffer,
            )
            if sl is not None:
                signal = {"side": "BUY", "entry": price, "sl": sl, "tp": tp, "idx": i}

        if signal:
            result, pnl, exit_idx = simulate_trade(
                df, i, signal["side"], signal["sl"], signal["tp"], signal["entry"]
            )
            trades.append({
                "result": result,
                "pnl": pnl,
                "side": signal["side"],
                "adx": adx_,
                "atr": atr_,
                "sl_dist": sd,
                "tp_dist": td,
                "rr": rr,
            })
            i = exit_idx + 1
        else:
            i += 1

    return trades


# ══════════════════════════════════════════════════════════════
#  Stats
# ══════════════════════════════════════════════════════════════
def calc_stats(trades):
    if not trades:
        return None
    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    timeouts = [t for t in trades if t["result"] == "TIMEOUT"]

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

    avg_rr = float(np.mean([t["rr"] for t in trades])) if trades else 0

    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "timeouts": len(timeouts),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "pnl": round(sum(t["pnl"] for t in trades), 2),
        "pf": round(total_win / total_loss, 2) if total_loss > 0 else 999,
        "max_dd": round(max_dd, 2),
        "avg_rr": round(avg_rr, 2),
    }


# ══════════════════════════════════════════════════════════════
#  Quick Test - v4 فعلی
# ══════════════════════════════════════════════════════════════
def quick_test_v4(timeframe: str = "15min"):
    print("=" * 60)
    print(f"🔍 Quick Test: v4 on {timeframe}")
    print("=" * 60)

    df = fetch_history(timeframe, outputsize=5000)
    df = add_indicators(df)
    print(f"📥 Loaded {len(df)} candles")
    print(f"   Range: {df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]}")

    trades = run_backtest(
        df,
        adx_min=15,
        sl_mult=1.5,
        tp_mult=2.5,
        adx_threshold=40,
        adx_boost=1.2,
        sl_structure_buffer=0.2,
    )

    if not trades:
        print("\n⚠️ No trades generated!")
        return None

    stats = calc_stats(trades)

    print("\n" + "─" * 60)
    print("📊 v4 RESULTS")
    print("─" * 60)
    print(f"  Total trades:  {stats['total']}")
    print(f"  Wins:          {stats['wins']} ✅")
    print(f"  Losses:        {stats['losses']} ❌")
    print(f"  Timeouts:      {stats['timeouts']} ⏰")
    print(f"  Win Rate:      {stats['win_rate']}%")
    print(f"  Total PnL:     {stats['pnl']:+.2f}")
    print(f"  Profit Factor: {stats['pf']}")
    print(f"  Max Drawdown:  {stats['max_dd']:.2f}")
    print(f"  Avg R:R:       {stats['avg_rr']}")
    print("─" * 60)

    return stats


# ══════════════════════════════════════════════════════════════
#  Grid Search
# ══════════════════════════════════════════════════════════════
def grid_search():
    print("=" * 70)
    print("🔬 GoldPro V2 - Grid Search (v4)")
    print("=" * 70)

    lines = ["🔬 <b>Grid Search v4 Results</b>\n"]

    tf = "15min"
    print(f"\n📊 Fetching {tf} data...")
    df = fetch_history(tf, outputsize=5000)
    df = add_indicators(df)
    print(f"📥 Got {len(df)} candles\n")

    # ── شبکه جستجو ──
    buffer_values = [0.1, 0.2, 0.5]
    adx_values = [15, 20]
    sl_values = [1.5, 2.0]
    tp_values = [2.5, 3.0, 3.5]
    boost_values = [1.0, 1.2]

    results = []
    total = (len(buffer_values) * len(adx_values) * len(sl_values)
             * len(tp_values) * len(boost_values))
    print(f"🔄 Testing {total} combinations...\n")

    for idx, (buf, adx, sl_m, tp_m, boost) in enumerate(
        itertools.product(buffer_values, adx_values, sl_values, tp_values, boost_values), 1
    ):
        trades = run_backtest(
            df, adx, sl_m, tp_m,
            adx_threshold=40, adx_boost=boost,
            sl_structure_buffer=buf,
        )
        stats = calc_stats(trades)
        if stats and stats["total"] >= 10:
            stats.update({
                "buf": buf, "adx": adx, "sl": sl_m,
                "tp": tp_m, "boost": boost,
            })
            results.append(stats)
            print(
                f"  [{idx}/{total}] Buf={buf} ADX={adx} SL={sl_m} TP={tp_m} "
                f"Boost={boost} -> Trades={stats['total']} WR={stats['win_rate']}% "
                f"PF={stats['pf']} DD={stats['max_dd']} avgRR={stats['avg_rr']}"
            )

    if not results:
        print("\n⚠️ No results with >= 10 trades")
        return

    results.sort(key=lambda x: (x["pf"], x["pnl"]), reverse=True)

    print("\n" + "=" * 70)
    print("🏆 TOP 10 COMBINATIONS")
    print("=" * 70)
    lines.append(f"📊 <b>{tf}</b>\n")
    lines.append("🏆 <b>Top 10:</b>")

    for i, r in enumerate(results[:10], 1):
        line = (
            f"\n{i}. Buf={r['buf']} ADX={r['adx']} SL={r['sl']} TP={r['tp']} Boost={r['boost']}\n"
            f"   Trades:{r['total']} WR:{r['win_rate']}% PF:<b>{r['pf']}</b> "
            f"avgRR:{r['avg_rr']}\n"
            f"   PnL:{r['pnl']} DD:{r['max_dd']}"
        )
        print(line)
        lines.append(line)

    best = results[0]
    print("\n🥇 BEST:")
    print(f"   SL_STRUCTURE_BUFFER = {best['buf']}")
    print(f"   ADX_MIN = {best['adx']}")
    print(f"   SL_ATR_MULT = {best['sl']}")
    print(f"   TP_ATR_MULT = {best['tp']}")
    print(f"   ADX_SL_BOOST = {best['boost']}")
    print(f"   WR={best['win_rate']}%  PF={best['pf']}  avgRR={best['avg_rr']}")

    lines.append("\n\n🥇 <b>BEST:</b>")
    lines.append(
        f"Buf={best['buf']} ADX={best['adx']} SL={best['sl']} "
        f"TP={best['tp']} Boost={best['boost']}"
    )
    lines.append(
        f"WR:{best['win_rate']}% PF:<b>{best['pf']}</b> avgRR:{best['avg_rr']}"
    )

    print("\n📨 Sending to Telegram...")
    send_telegram("\n".join(lines))
    print("✅ Done")


# ══════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_test_v4()
    elif len(sys.argv) > 1 and sys.argv[1] == "grid":
        grid_search()
    else:
        print("Usage:")
        print("  python grid_search.py quick    -> quick test v4")
        print("  python grid_search.py grid     -> full grid search")
        print()
        print("Default: running quick test...")
        quick_test_v4()