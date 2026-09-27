from src.config import (
    ADX_MIN, RSI_BUY_MIN, RSI_BUY_MAX,
    RSI_SELL_MIN, RSI_SELL_MAX,
    SL_ATR_MULT, TP_ATR_MULT,
)


def evaluate_signal(df):
    """آخرین کندل بسته‌شده را ارزیابی می‌کند (کندل در حال تشکیل نادیده گرفته می‌شود)"""
    row = df.iloc[-2]  # -1 در حال تشکیل است

    price = row["close"]
    ema_f = row["ema_fast"]
    ema_s = row["ema_slow"]
    rsi_ = row["rsi"]
    adx_ = row["adx"]
    macd_ = row["macd"]
    macd_sig = row["macd_signal"]
    macd_h = row["macd_hist"]
    atr_ = row["atr"]

    buy = (
        ema_f > ema_s
        and RSI_BUY_MIN < rsi_ < RSI_BUY_MAX
        and adx_ > ADX_MIN
        and macd_ > macd_sig
        and macd_h > 0
    )

    sell = (
        ema_f < ema_s
        and RSI_SELL_MIN < rsi_ < RSI_SELL_MAX
        and adx_ > ADX_MIN
        and macd_ < macd_sig
        and macd_h < 0
    )

    if buy:
        return {
            "side": "BUY",
            "entry": round(price, 2),
            "sl": round(price - SL_ATR_MULT * atr_, 2),
            "tp": round(price + TP_ATR_MULT * atr_, 2),
            "rsi": round(rsi_, 1),
            "adx": round(adx_, 1),
            "atr": round(atr_, 2),
            "time": str(row["datetime"]),
        }

    if sell:
        return {
            "side": "SELL",
            "entry": round(price, 2),
            "sl": round(price + SL_ATR_MULT * atr_, 2),
            "tp": round(price - TP_ATR_MULT * atr_, 2),
            "rsi": round(rsi_, 1),
            "adx": round(adx_, 1),
            "atr": round(atr_, 2),
            "time": str(row["datetime"]),
        }

    return None
