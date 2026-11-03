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
    تشخیص سیگنال ایچیموکو بر اساس کراس تنکان/کیجون + تایید ابر کومو.
    
    - BUY: کراس صعودی تنکان/کیجون + قیمت بالای ابر (روند صعودی)
    - SELL: کراس نزولی تنکان/کیجون + قیمت زیر ابر (روند نزولی)
    
    اینطوری فقط در جهت روند معامله می‌کنیم و از نویزهای داخل ابر جلوگیری می‌شه.
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
    
    prev_tenkan = float(prev["tenkan"])
    prev_kijun = float(prev["kijun"])

    if any(pd.isna(x) for x in [tenkan, kijun, senkou_a, senkou_b, prev_tenkan, prev_kijun]):
        return None

    kumo_top = max(senkou_a, senkou_b)
    kumo_bottom = min(senkou_a, senkou_b)

    # 🚨 منطق جدید: کراس + تایید روند با ابر
    
    cross_up = (prev_tenkan <= prev_kijun) and (tenkan > kijun)
    cross_down = (prev_tenkan >= prev_kijun) and (tenkan < kijun)
    
    # فقط اگه قیمت بالای ابر باشه (روند صعودی)
    if cross_up and (close > kumo_top):
        return {
            "pattern": "ichimoku_trend_buy",
            "strategy": "ICHIMOKU",
            "direction": "BUY",
            "tenkan": round(tenkan, 2),
            "kijun": round(kijun, 2),
        }

    # فقط اگه قیمت زیر ابر باشه (روند نزولی)
    if cross_down and (close < kumo_bottom):
        return {
            "pattern": "ichimoku_trend_sell",
            "strategy": "ICHIMOKU",
            "direction": "SELL",
            "tenkan": round(tenkan, 2),
            "kijun": round(kijun, 2),
        }

    return None