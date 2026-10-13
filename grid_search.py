"""
GoldPro V2 - Grid Search Optimization (v3-aligned)
بهینه‌سازی پارامترهای v3 روی داده تاریخی
"""
import itertools
import requests
import pandas as pd
import numpy as np

from src.config import (
    TWELVEDATA_KEY, SYMBOL,
    ATR_MIN_USD, ATR_MAX_USD,
    MIN_SL_USD, MIN_TP_USD,
    SL_STRUCTURE_BUFFER, BLOCKED_HOURS_UTC,
    compute_atr_effective,
)
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


def is_blocked_hour(dt) -> bool:
    """چک کن ساعت UTC ممنوعه هست یا نه."""
    try:
        return dt.hour in BLOCKED_HOURS_UTC
    except Exception:
        return False


def compute_sl_tp_v3(side, price, atr, adx_value,
                     recent_high=None, recent_low=None,
                     sl_base_mult=1.5, tp_mult=2.5,
                     adx_threshold=40, adx_boost=1.5):
    """
    دقیقاً همون منطق v3، ولی پارامترها قابل تنظیم.
    """
    if atr is None or atr <= 0 or price <= 0:
        return None, None, None, None, None

    # ADX-aware ضریب
    if adx_value is not None and adx_value > adx_threshold:
        sl_mult = sl_base_mult * adx_boost
    else:
        sl_mult = sl_base_mult

    # --- SL ---
    if side == "SELL":
        sl_structure = (recent_high + SL_STRUCTURE_BUFFER * atr
                        if recent_high else price + MIN_SL_USD)
        sl_atr = price + sl_mult * atr
        sl = max(sl_structure, sl_atr)
        if (sl - price) < MIN_SL_USD:
            sl = price + MIN_SL_USD
        sl_dist = sl - price
    elif side == "BUY":
        sl_structure = (recent_low - SL_STRUCTURE_BUFFER * atr
                        if recent_low else price - MIN_SL_USD)
        sl_atr = price - sl_mult * atr
        sl = min(sl_structure, sl_atr)
        if (price - sl) < MIN_SL_USD:
            sl = price - MIN_SL_USD
        sl_dist = price - sl
    else:
        return None, None, None, None, None

    # --- TP ---
    tp_dist = max(tp_mult * atr, MIN_TP_USD)
    tp = price + tp_dist if side == "BUY" else price - tp_dist

    rr = tp_dist / sl_dist if sl_dist > 0 else 0
    return sl, tp, sl_dist, tp_dist, rr


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
                 adx_threshold=40, adx_boost=1.5,
                 max_bars_since=2, atr_min=ATR_MIN_USD, atr_max=ATR_MAX_USD,
                 block_hours=None):
    """
    بک‌تست هم‌راستا با v3.
    """
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

        # ── ATR clamp ──
        if atr_raw < atr_min:
            i += 1
            continue
        atr_ = min(atr_raw, atr_max)

        # ── ADX filter ──
        if adx_ < adx_min:
            i += 1
            continue

        # ── Blocked hours ──
        if is_blocked_hour(current["datetime"]):
            i += 1
            continue

        # ── Strategy ──
        rsi_series = window["rsi"].iloc[:-1]
        sell_setup = detect_double_top_sell(rsi_series, max_bars_since_peak=max_bars_since)
        buy_setup = detect_double_bottom_buy(rsi_series, max_bars_since_trough=max_bars_since)

        signal = None
        if sell_setup:
            recent_high = float(window["high"].tail(20).max())
            sl, tp, sd, td, rr = compute_sl_tp_v3(
                "SELL", price, atr_, adx_,
                recent_high=recent_high,
                sl_base_mult=sl_mult, tp_mult=tp_mult,
                adx_threshold=adx_threshold, adx_boost=adx_boost,
            )
            if sl is not None:
                signal = {"side": "SELL", "entry": price, "sl": sl, "tp": tp, "idx": i}
        elif buy_setup:
            recent_low = float(window["low"].tail(20).min())
            sl, tp, sd, td, rr = compute_sl_tp_v3(
                "BUY", price, atr_, adx_,
                recent_low=recent_low,
                sl_base_mult=sl_mult, tp_mult=tp_mult,
                adx_threshold=adx_threshold, adx_boost=adx_boost,
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

    # میانگین R:R واقعی
    avg_rr = np.mean([t["rr"] for t in trades]) if trades else 0

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


def main():
    print("=" * 70)
    print("🔬 GoldPro V2 - Grid Search (v3-aligned)")
    print("=" * 70)

    lines = ["🔬 <b>Grid Search v3 Results</b>\n"]

    tf = "15min"
    print(f"\n📊 Fetching {tf} data...")
    df = fetch_history(tf, outputsize=5000)
    df = add_indicators(df)
    print(f"📥 Got {len(df)} candles\n")

    # ── شبکه جستجو ──
    adx_values = [15, 20]
    sl_values = [1.0, 1.5, 2.0]       # پایه (نه 2.5-3.0)
    tp_values = [2.0, 2.5, 3.0]
    boost_values = [1.0, 1.5, 2.0]    # ADX boost

    results = []
    total_combos = len(adx_values) * len(sl_values) * len(tp_values) * len(boost_values)
    print(f"🔄 Testing {total_combos} combinations...\n")

    for idx, (adx, sl_m, tp_m, boost) in enumerate(
        itertools.product(adx_values, sl_values, tp_values, boost_values), 1
    ):
        trades = run_backtest(
            df, adx, sl_m, tp_m,
            adx_threshold=40, adx_boost=boost,
        )
        stats = calc_stats(trades)
        if stats and stats["total"] >= 10:
            stats["adx"] = adx
            stats["sl"] = sl_m
            stats["tp"] = tp_m
            stats["boost"] = boost
            results.append(stats)
            print(
                f"  [{idx}/{total_combos}] ADX={adx} SL={sl_m} TP={tp_m} Boost={boost} -> "
                f"Trades={stats['total']} WR={stats['win_rate']}% PF={stats['pf']} "
                f"DD={stats['max_dd']} avgRR={stats['avg_rr']}"
            )

    # مرتب‌سازی: اول PF، بعد PnL
    results.sort(key=lambda x: (x["pf"], x["pnl"]), reverse=True)

    print("\n" + "=" * 70)
    print("🏆 TOP 10 COMBINATIONS")
    print("=" * 70)
    lines.append(f"📊 <b>{tf}</b>\n")
    lines.append("🏆 <b>Top 10:</b>")

    for i, r in enumerate(results[:10], 1):
        line = (
            f"\n{i}. ADX={r['adx']} SL={r['sl']}xATR TP={r['tp']}xATR Boost={r['boost']}\n"
            f"   Trades:{r['total']} WR:{r['win_rate']}% PF:<b>{r['pf']}</b> "
            f"avgRR:{r['avg_rr']}\n"
            f"   PnL:{r['pnl']} DD:{r['max_dd']}"
        )
        print(line)
        lines.append(line)

    # بهترین ترکیب
    if results:
        best = results[0]
        print("\n🥇 BEST:")
        print(f"   ADX_MIN = {best['adx']}")
        print(f"   SL_ATR_MULT = {best['sl']}")
        print(f"   TP_ATR_MULT = {best['tp']}")
        print(f"   ADX_SL_BOOST = {best['boost']}")
        print(f"   WR: {best['win_rate']}%  PF: {best['pf']}  avgRR: {best['avg_rr']}")

        lines.append("\n\n🥇 <b>BEST:</b>")
        lines.append(f"ADX_MIN={best['adx']} SL={best['sl']} TP={best['tp']} Boost={best['boost']}")
        lines.append(f"WR:{best['win_rate']}% PF:<b>{best['pf']}</b> avgRR:{best['avg_rr']}")

        # ── مقایسه با v3 فعلی ──
        print("\n📌 Current v3 (for comparison):")
        print("   SL_ATR_MULT=1.5, TP_ATR_MULT=2.5, ADX_BOOST=1.5, ADX_MIN=15")
        v3_match = [r for r in results
                    if r["sl"] == 1.5 and r["tp"] == 2.5
                    and r["boost"] == 1.5 and r["adx"] == 15]
        if v3_match:
            v3 = v3_match[0]
            print(f"   v3 stats: WR={v3['win_rate']}% PF={v3['pf']} DD={v3['max_dd']} avgRR={v3['avg_rr']}")
            lines.append(f"\n\n📌 <b>v3 current</b>:")
            lines.append(f"WR:{v3['win_rate']}% PF:{v3['pf']} avgRR:{v3['avg_rr']}")

    print("\n📨 Sending to Telegram...")
    send_telegram("\n".join(lines))
    print("✅ Done")


if __name__ == "__main__":
    main()
def quick_test_v3():
    """تست سریع v3 روی 15min"""
    print("🔍 Quick test v3...")
    df = fetch_history("15min", outputsize=5000)
    df = add_indicators(df)
    print(f"📥 {len(df)} candles")

    trades = run_backtest(df, adx_min=15, sl_mult=1.5, tp_mult=2.5,
                          adx_threshold=40, adx_boost=1.5)
    stats = calc_stats(trades)
    print("\n" + "="*50)
    print("v3 RESULT (15min):")
    print("="*50)
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return stats