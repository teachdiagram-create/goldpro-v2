"""
GoldPro V2 — Backtest Engine
استراتژی: RSI Double Top/Bottom
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime

from src.config import (
    TWELVEDATA_KEY, SYMBOL,
    SL_ATR_MULT, TP_ATR_MULT,
)
from src.indicators import add_indicators
from src.strategy import detect_double_top_sell, detect_double_bottom_buy
from src.telegram_bot import send_telegram


# ══════════════════════════════════════════════════════════════
#  دریافت داده تاریخی بیشتر
# ══════════════════════════════════════════════════════════════
def fetch_history(timeframe: str = "5min", outputsize: int = 5000) -> pd.DataFrame:
    """دریافت داده تاریخی (بیشتر از حالت عادی)"""
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


# ══════════════════════════════════════════════════════════════
#  شبیه‌سازی یک معامله (Entry → SL یا TP)
# ══════════════════════════════════════════════════════════════
def simulate_trade(df: pd.DataFrame, entry_idx: int, side: str,
                   sl: float, tp: float, entry_price: float,
                   max_bars: int = 200) -> dict:
    """
    شبیه‌سازی معامله از کندل entry_idx تا زدن SL یا TP
    Returns dict با result (WIN/LOSS/TIMEOUT), exit_price, exit_idx, bars
    """
    for i in range(entry_idx + 1, min(entry_idx + max_bars, len(df))):
        bar = df.iloc[i]
        high = float(bar["high"])
        low = float(bar["low"])

        if side == "BUY":
            if low <= sl:
                return {
                    "result": "LOSS",
                    "exit_price": sl,
                    "exit_idx": i,
                    "bars": i - entry_idx,
                    "pnl": sl - entry_price,
                }
            if high >= tp:
                return {
                    "result": "WIN",
                    "exit_price": tp,
                    "exit_idx": i,
                    "bars": i - entry_idx,
                    "pnl": tp - entry_price,
                }
        else:  # SELL
            if high >= sl:
                return {
                    "result": "LOSS",
                    "exit_price": sl,
                    "exit_idx": i,
                    "bars": i - entry_idx,
                    "pnl": entry_price - sl,
                }
            if low <= tp:
                return {
                    "result": "WIN",
                    "exit_price": tp,
                    "exit_idx": i,
                    "bars": i - entry_idx,
                    "pnl": entry_price - tp,
                }

    # timeout: با آخرین قیمت ببند
    last_bar = df.iloc[min(entry_idx + max_bars, len(df) - 1)]
    exit_price = float(last_bar["close"])

    if side == "BUY":
        pnl = exit_price - entry_price
    else:
        pnl = entry_price - exit_price

    return {
        "result": "TIMEOUT",
        "exit_price": exit_price,
        "exit_idx": entry_idx + max_bars,
        "bars": max_bars,
        "pnl": pnl,
    }


# ══════════════════════════════════════════════════════════════
#  اجرای بک‌تست روی یک تایم‌فریم
# ══════════════════════════════════════════════════════════════
def backtest_timeframe(df: pd.DataFrame, timeframe: str) -> dict:
    """شبیه‌سازی کامل روی داده تاریخی"""
    trades = []

    # شروع از کندل 100 (برای محاسبه اندیکاتورها نیاز داریم)
    # و پایان 100 کندل قبل آخر (برای اجازه تکمیل معامله)
    start_idx = 100
    end_idx = len(df) - 100

    if end_idx <= start_idx:
        return {"trades": [], "error": "Not enough data"}

    i = start_idx
    while i < end_idx:
        # داده تا این کندل رو می‌گیریم
        window = df.iloc[:i + 1]
        current = window.iloc[-1]
        rsi_series = window["rsi"].iloc[:-1]  # فقط بسته‌شده‌ها

        price = float(current["close"])
        atr_ = float(current["atr"])

        if pd.isna(atr_) or atr_ <= 0:
            i += 1
            continue

        sell_setup = detect_double_top_sell(rsi_series)
        buy_setup = detect_double_bottom_buy(rsi_series)

        signal = None
        if sell_setup:
            recent_high = float(window["high"].tail(20).max())
            sl = round(recent_high + 0.5 * atr_, 2)
            risk = sl - price
            if risk <= 0:
                risk = 1.0 * atr_
                sl = round(price + risk, 2)
            tp = round(price - TP_ATR_MULT * atr_, 2)
            signal = {
                "side": "SELL",
                "entry": price,
                "sl": sl,
                "tp": tp,
                "idx": i,
                "time": str(current["datetime"]),
            }
        elif buy_setup:
            recent_low = float(window["low"].tail(20).min())
            sl = round(recent_low - 0.5 * atr_, 2)
            risk = price - sl
            if risk <= 0:
                risk = 1.0 * atr_
                sl = round(price - risk, 2)
            tp = round(price + TP_ATR_MULT * atr_, 2)
            signal = {
                "side": "BUY",
                "entry": price,
                "sl": sl,
                "tp": tp,
                "idx": i,
                "time": str(current["datetime"]),
            }

        if signal:
            # شبیه‌سازی معامله
            result = simulate_trade(
                df, i, signal["side"],
                signal["sl"], signal["tp"], signal["entry"]
            )
            trades.append({**signal, **result})

            # رد کردن کندل‌ها تا بعد از بسته شدن معامله
            i = result["exit_idx"] + 1
        else:
            i += 1

    return {"trades": trades}


# ══════════════════════════════════════════════════════════════
#  محاسبه آمار
# ══════════════════════════════════════════════════════════════
def calculate_stats(trades: list) -> dict:
    if not trades:
        return {
            "total": 0, "wins": 0, "losses": 0, "timeouts": 0,
            "win_rate": 0, "total_pnl": 0, "profit_factor": 0,
            "avg_win": 0, "avg_loss": 0, "best": 0, "worst": 0,
            "max_drawdown": 0,
        }

    wins = [t for t in trades if t["result"] == "WIN"]
    losses = [t for t in trades if t["result"] == "LOSS"]
    timeouts = [t for t in trades if t["result"] == "TIMEOUT"]

    total_win_pnl = sum(t["pnl"] for t in wins)
    total_loss_pnl = abs(sum(t["pnl"] for t in losses))

    # Equity curve برای Max Drawdown
    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t["pnl"])

    peak = equity[0]
    max_dd = 0
    for val in equity:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "timeouts": len(timeouts),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "total_pnl": round(sum(t["pnl"] for t in trades), 2),
        "profit_factor": round(total_win_pnl / total_loss_pnl, 2) if total_loss_pnl > 0 else float("inf"),
        "avg_win": round(total_win_pnl / len(wins), 2) if wins else 0,
        "avg_loss": round(total_loss_pnl / len(losses), 2) if losses else 0,
        "best": round(max(t["pnl"] for t in trades), 2) if trades else 0,
        "worst": round(min(t["pnl"] for t in trades), 2) if trades else 0,
        "max_drawdown": round(max_dd, 2),
    }


# ══════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("🧪 GoldPro V2 — Backtest")
    print("=" * 60)

    lines = ["🧪 <b>GoldPro V2 — Backtest Results</b>\n"]
    lines.append(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")

    for tf in ["5min", "15min"]:
        print(f"\n{'═' * 60}")
        print(f"📊 Timeframe: {tf}")
        print(f"{'═' * 60}")

        try:
            df = fetch_history(tf, outputsize=5000)
            df = add_indicators(df)
            print(f"📥 دریافت {len(df)} کندل ({df['datetime'].iloc[0]} تا {df['datetime'].iloc[-1]})")

            result = backtest_timeframe(df, tf)

            if "error" in result:
                print(f"❌ {result['error']}")
                lines.append(f"\n📊 <b>{tf}</b>\n❌ {result['error']}")
                continue

            stats = calculate_stats(result["trades"])

            print(f"\n📈 نتایج:")
            print(f"  Total Trades:     {stats['total']}")
            print(f"  Wins:             {stats['wins']}  ✅")
            print(f"  Losses:           {stats['losses']}  ❌")
            print(f"  Timeouts:         {stats['timeouts']}  ⏱")
            print(f"  Win Rate:         {stats['win_rate']}%")
            print(f"  Total PnL:        {stats['total_pnl']}")
            print(f"  Profit Factor:    {stats['profit_factor']}")
            print(f"  Avg Win:          {stats['avg_win']}")
            print(f"  Avg Loss:         {stats['avg_loss']}")
            print(f"  Best Trade:       {stats['best']}")
            print(f"  Worst Trade:      {stats['worst']}")
            print(f"  Max Drawdown:     {stats['max_drawdown']}")

            lines.append(f"\n📊 <b>{tf}</b>")
            lines.append(f"📥 کندل‌ها: {len(df)}")
            lines.append(f"🎯 معاملات: {stats['total']}")
            lines.append(f"✅ برد: {stats['wins']} | ❌ باخت: {stats['losses']}")
            lines.append(f"💯 Win Rate: <b>{stats['win_rate']}%</b>")
            lines.append(f"💰 PnL: {stats['total_pnl']}")
            lines.append(f"📊 Profit Factor: <b>{stats['profit_factor']}</b>")
            lines.append(f"📉 Max DD: {stats['max_drawdown']}")

        except Exception as e:
            print(f"❌ Error: {e}")
            lines.append(f"\n📊 <b>{tf}</b>\n❌ {e}")

    print("\n📨 Sending backtest report to Telegram...")
    send_telegram("\n".join(lines))
    print("✅ Done")


if __name__ == "__main__":
    main()