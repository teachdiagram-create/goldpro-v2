"""
Risk Manager - مدیریت ریسک به ازای هر استراتژی (نه کل ربات)
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


def can_open_trade(state: dict, strategy: str, max_open: int = 1) -> tuple[bool, str]:
    """
    بررسی آیا استراتژی می‌تونه ترید جدید باز کنه (بر اساس محدودیت خودش).
    """
    open_count = count_open_trades_by_strategy(state, strategy)
    if open_count >= max_open:
        return False, f"{strategy}: {open_count}/{max_open} open"
    return True, "OK"