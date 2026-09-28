from src.config import SL_ATR_MULT, TP_ATR_MULT
from src.strategy import detect_double_top_sell, detect_double_bottom_buy


def evaluate_signal(df, timeframe: str = "5min"):
    """
    ارزیابی آخرین کندل بسته‌شده با استراتژی RSI Double Top/Bottom
    """
    closed = df.iloc[:-1]
    current = closed.iloc[-1]

    rsi_series = closed["rsi"]

    price = float(current["close"])
    atr_ = float(current["atr"])
    adx_ = float(current["adx"])
    rsi_ = float(current["rsi"])

    base = {
        "timeframe": timeframe,
        "rsi": round(rsi_, 1),
        "adx": round(adx_, 1),
        "atr": round(atr_, 2),
        "time": str(current["datetime"]),
    }

    # ── چک SELL: دابل تاپ ──
    sell_setup = detect_double_top_sell(rsi_series)
    if sell_setup:
        recent_high = float(closed["high"].tail(20).max())
        sl = round(recent_high + 0.5 * atr_, 2)
        risk = sl - price
        if risk <= 0:
            risk = 1.0 * atr_
            sl = round(price + risk, 2)
        tp = round(price - TP_ATR_MULT * atr_, 2)

        return {
            **base,
            "side": "SELL",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "reason": (
                f"RSI double top: {sell_setup['peak1_value']} → "
                f"{sell_setup['peak2_value']} (now {sell_setup['current_rsi']})"
            ),
        }

    # ── چک BUY: دابل باتم ──
    buy_setup = detect_double_bottom_buy(rsi_series)
    if buy_setup:
        recent_low = float(closed["low"].tail(20).min())
        sl = round(recent_low - 0.5 * atr_, 2)
        risk = price - sl
        if risk <= 0:
            risk = 1.0 * atr_
            sl = round(price - risk, 2)
        tp = round(price + TP_ATR_MULT * atr_, 2)

        return {
            **base,
            "side": "BUY",
            "entry": round(price, 2),
            "sl": sl,
            "tp": tp,
            "reason": (
                f"RSI double bottom: {buy_setup['trough1_value']} → "
                f"{buy_setup['trough2_value']} (now {buy_setup['current_rsi']})"
            ),
        }

    return None