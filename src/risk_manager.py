"""
Risk Manager - مدیریت ریسک و جلوگیری از تریدهای همزمان.
"""
from datetime import datetime


def has_open_trade(state: dict) -> bool:
    """
    آیا ترید بازی وجود داره؟
    ترید باز = تریدی که result اون None هست.
    """
    history = state.get("history", [])
    for trade in history:
        if trade.get("result") is None:
            return True
    return False


def count_open_trades(state: dict) -> int:
    """تعداد تریدهای باز"""
    history = state.get("history", [])
    return sum(1 for t in history if t.get("result") is None)


def can_send_signal(signal: dict, state: dict, max_open: int = 1) -> tuple[bool, str]:
    """
    بررسی آیا می‌تونیم سیگنال جدید بفرستیم.
    
    Returns:
        (allowed, reason)
    """
    open_count = count_open_trades(state)
    if open_count >= max_open:
        return False, f"Open trades: {open_count}/{max_open}"

    return True, "OK"