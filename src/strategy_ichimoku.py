import pandas as pd


def calculate_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    """
    محاسبه خطوط ایچیموکو.
    """
    df = df.copy()
    # Tenkan-sen (9)
    high_9 = df["high"].rolling(window=9).max()
    low_9 = df["low"].rolling(window=9).min()
    df["tenkan"] = (high_9 + low_9) / 2

    # Kijun-sen (26)
    high_26 = df["high"].rolling(window=26).max()
    low_26 = df["low"].rolling(window=26).min()
    df["kijun"] = (high_26 + low_26) / 2

    # Senkou Span A (شیفت ۲۶ به جلو)
    df["senkou_a"] = ((df["tenkan"] + df["kijun"]) / 2).shift(26)

    # Senkou Span B (52 دوره، شیفت ۲۶ به جلو)
    high_52 = df["high"].rolling(window=52).max()
    low_52 = df["low"].rolling(window=52).min()
    df["senkou_b"] = ((high_52 + low_52) / 2).shift(26)

    return df


def detect_ichimoku_signal(df_m5: pd.DataFrame) -> dict:
    """
    تشخیص سیگنال ایچیموکو بر اساس استراتژی «شکست ابر کومو» (Kumo Breakout).
    
    - BUY: کندل قبلی زیر ابر بوده، کندل فعلی بالای ابر بسته شده، و تنکان > کیجون.
    - SELL: کندل قبلی بالای ابر بوده، کندل فعلی زیر ابر بسته شده، و تنکان < کیجون.
    """
    if len(df_m5) < 60:
        return None

    if "tenkan" not in df_m5.columns:
        df_m5 = calculate_ichimoku(df_m5)

    closed = df_m5.iloc[:-1]
    last = closed.iloc[-1]
    prev = closed.iloc[-2]

    tenkan = float(last["tenkan"])
    kijun = float(last["kijun"])
    senkou_a = float(last["senkou_a"])
    senkou_b = float(last["senkou_b"])
    close = float(last["close"])
    prev_close = float(prev["close"])
    
    prev_tenkan = float(prev["tenkan"])
    prev_kijun = float(prev["kijun"])

    # اگه دیتا ناقص بود، سیگنال نده
    if any(pd.isna(x) for x in [tenkan, kijun, senkou_a, senkou_b, prev_tenkan, prev_kijun]):
        return None

    kumo_top = max(senkou_a, senkou_b)
    kumo_bottom = min(senkou_a, senkou_b)

    # 🚨 منطق جدید: شکست ابر کومو (Kumo Breakout)
    
    # BUY: کندل قبلی زیر ابر، کندل فعلی بالای ابر، تنکان بالای کیجون
    breakout_up = (prev_close <= kumo_top) and (close > kumo_top) and (tenkan > kijun)
    
    # SELL: کندل قبلی بالای ابر، کندل فعلی زیر ابر، تنکان زیر کیجون
    breakout_down = (prev_close >= kumo_bottom) and (close < kumo_bottom) and (tenkan < kijun)

    if breakout_up:
        return {
            "pattern": "ichimoku_breakout",
            "strategy": "ICHIMOKU",
            "direction": "BUY",
            "tenkan": round(tenkan, 2),
            "kijun": round(kijun, 2),
        }

    if breakout_down:
        return {
            "pattern": "ichimoku_breakout",
            "strategy": "ICHIMOKU",
            "direction": "SELL",
            "tenkan": round(tenkan, 2),
            "kijun": round(kijun, 2),
        }

    return None