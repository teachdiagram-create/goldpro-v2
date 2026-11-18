def _compute_quality(adx_val: float, atr_val: float, rsi_val: float, 
                     side: str, strategy: str, divergence: bool = False) -> dict:
    """
    محاسبه کیفیت سیگنال بر اساس ترکیب شرایط بازار (نه فقط جمع امتیاز خام).
    امتیاز نهایی به احتمال موفقیت نزدیک‌تره.
    """
    score = 50
    flags = []
    warnings = []
    weighted_score = 0
    total_weight = 0

    # ─── ۱. وزن‌دهی به ADX (مهم‌ترین فاکتور) ───
    if adx_val is None: 
        warnings.append("ADX نامشخص")
    else:
        # وزن ADX = 0.4
        total_weight += 0.4
        if adx_val >= 50: weighted_score += 0.4 * 100; flags.append("ADX قوی")
        elif adx_val >= 35: weighted_score += 0.4 * 85; flags.append("ADX خوب")
        elif adx_val >= 25: weighted_score += 0.4 * 65
        elif adx_val >= 15: weighted_score += 0.4 * 40; warnings.append("ADX ضعیف")
        else: weighted_score += 0.4 * 15; warnings.append("ADX خیلی ضعیف")

    # ─── ۲. وزن‌دهی به ATR (فاکتور دوم) ───
    if atr_val is None: 
        warnings.append("ATR نامشخص")
    else:
        # وزن ATR = 0.25
        total_weight += 0.25
        if atr_val < 0.5: weighted_score += 0.25 * 20; warnings.append("ATR خیلی کم")
        elif atr_val < 1.0: weighted_score += 0.25 * 40; warnings.append("ATR کم")
        elif atr_val <= 4.0: weighted_score += 0.25 * 85; flags.append("ATR مناسب")
        elif atr_val <= 6.0: weighted_score += 0.25 * 55; warnings.append("ATR بالا")
        else: weighted_score += 0.25 * 30; warnings.append("ATR خیلی بالا")

    # ─── ۳. وزن‌دهی به RSI (فاکتور سوم) ───
    if rsi_val is not None:
        total_weight += 0.2
        if strategy == "RANGE":
            if side == "SELL" and rsi_val <= 65: weighted_score += 0.2 * 80; flags.append("RSI تأیید می‌کند")
            elif side == "BUY" and rsi_val >= 35: weighted_score += 0.2 * 80; flags.append("RSI تأیید می‌کند")
            else: weighted_score += 0.2 * 40
        else:
            if side == "BUY" and 40 <= rsi_val <= 70: weighted_score += 0.2 * 80; flags.append("RSI در محدوده")
            elif side == "SELL" and 30 <= rsi_val <= 60: weighted_score += 0.2 * 80; flags.append("RSI در محدوده")
            else: weighted_score += 0.2 * 40

    # ─── ۴. واگرایی (فاکتور تقویتی، وزن کمتر) ───
    if divergence:
        total_weight += 0.1
        weighted_score += 0.1 * 95
        flags.append("واگرایی تایید شد")
    else:
        total_weight += 0.1
        weighted_score += 0.1 * 45

    # ─── ۵. نرمال‌سازی امتیاز ───
    if total_weight > 0:
        final_score = weighted_score / total_weight
    else:
        final_score = 50

    final_score = max(0, min(100, round(final_score, 1)))

    # ─── ۶. تعیین گرید بر اساس امتیاز نهایی ───
    if final_score >= 80: grade = "A"
    elif final_score >= 65: grade = "B"
    elif final_score >= 50: grade = "C"
    else: grade = "D"

    return {
        "score": final_score,
        "grade": grade,
        "flags": flags,
        "warnings": warnings,
    }