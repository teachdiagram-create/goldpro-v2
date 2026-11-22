def format_timeout_message(trade: dict) -> str:
    """پیام بسته شدن معامله با Timeout"""
    tf = trade.get("timeframe", "5min").replace("min", "M")
    strategy = trade.get("strategy", "RANGE")
    pnl = trade.get("pnl", 0)
    pnl_str = f"+{pnl}" if pnl > 0 else str(pnl)
    signal_id = trade.get("signal_id", "N/A")
    strategy_name = _get_strategy_name(strategy)

    return (
        f"⏰ <b>GOLD {trade['side']} — TIMEOUT</b> ({tf})\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 کد سیگنال: <b>{signal_id}</b>\n"
        f"🎯 استراتژی: <b>{strategy_name}</b>\n"
        f"💵 Entry: {trade.get('entry')}\n"
        f"🏁 Exit: {trade.get('exit_price')}\n"
        f"💰 سود/ضرر: <b>{pnl_str}</b>\n"
        f"🕐 {trade.get('exit_time', '')}"
    )