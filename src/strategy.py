def detect_double_top_sell(rsi_series, lookback=50, threshold=70.0,
                          max_bars_since_peak=2, min_decline=1.0):
    """
    Returns:
        dict با کلیدهای peak1_value, peak2_value, current_rsi, bars_since_peak
        یا None اگه الگو نباشه
    """
    ...

def detect_double_bottom_buy(rsi_series, lookback=50, threshold=30.0,
                            max_bars_since_trough=2, min_rise=1.0):
    """
    Returns:
        dict با کلیدهای trough1_value, trough2_value, current_rsi, bars_since_trough
        یا None
    """
    ...