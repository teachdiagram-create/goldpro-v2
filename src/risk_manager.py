"""
Risk Manager - مدیریت ریسک و جلوگیری از تریدهای همزمان
(به ازای هر استراتژی)
"""
from datetime import datetime


def count_open_trades_by_strategy(state: dict, strategy: str) -> int:
    """تعداد تریدهای باز برای یک استراتژی خاص"""
    history = state.get("history", [])
    count = 0
    for t in history:
        if t.get("result") is None and t.get("strategy") == strategy:
            count += 1
    return count


def has_open_trade_for_strategy(state: dict, strategy: str, max_open: int = 1) -> bool:
    """آیا این استراتژی به سقف ترید باز خودش رسیده؟"""
    return count_open_trades_by_strategy(state, strategy) >= max_open


def can_open_trade(state: dict, strategy: str, max_open: int = 1) -> tuple[bool, str]:
    """
    بررسی آیا استراتژی می‌تونه ترید جدید باز کنه.
    Returns: (allowed, reason)
    """
    open_count = count_open_trades_by_strategy(state, strategy)
    if open_count >= max_open:
        return False, f"{strategy}: {open_count}/{max_open} open"
    return True, "OK"