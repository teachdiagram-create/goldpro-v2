import requests
from src.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DASHBOARD_URL


def _emoji(side: str) -> str:
    return "🟢" if side == "BUY" else "🔴"


def _grade_emoji(grade: str) -> str:
    return {"A": "🏆", "B": "✅", "C": "⚠️", "D": "🚫"}.get(grade, "❔")


def _get_strategy_name(strategy: str) -> str:
    if strategy == "TREND":
        return "📈 Trend (EMA+MACD)"
    elif strategy == "CORRELATION":
        return "📊 Correlation (DXY)"
    elif strategy == "ICHIMOKU":
        return "☁️ Ichimoku (Kumo)"
    return "🔄 Range (RSI)"


def format_message(sig: dict) -> str:
    tf = sig.get("timeframe", "5min").replace("min", "M")
    entry = sig.get("entry", "?")
    sl = sig.get("sl", "?")
    tp = sig.get("tp", "?")
    strategy = sig.get("strategy", "RANGE")
    signal_id = sig.get("signal_id", "N/A")
    
    strategy_name = _get_strategy_name(strategy)

    rr_text = ""
    if sig.get("rr") is not None:
        rr_text = f"⚖️ R:R = 1 : {sig['rr']:.2f}"

    sl_line = f"🛑 SL: {sl}"
    tp_line = f"🎯 TP: {tp}"
    if sig.get("sl_distance") is not None:
        sl_line += f"  <i>({sig['sl_distance']})</i>"
    if sig.get("tp_distance") is not None:
        tp_line += f"  <i>({sig['tp_distance']})</i>"

    q = sig.get("quality") or {}
    score = q.get("score", 0)
    grade = q.get("grade", "?")
    flags = q.get("flags", [])
    warnings = q.get("warnings", [])

    lines = [
        f"{_emoji(sig['side'])} <b>GOLD {sig['side']} — {tf}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"🆔 کد سیگنال: <b>{signal_id}</b>",
        f"🎯 استراتژی: <b>{strategy_name}</b>",
        f"💵 Entry: <b>{entry}</b>",
        sl_line,
        tp_line,
    ]
    if rr_text:
        lines.append(rr_text)
    
    lines.append(f"⭐ کیفیت: <b>{score}/100</b>  {_grade_emoji(grade)} <b>{grade}</b>")

    if flags:
        lines.append(f"✅ {' | '.join(flags)}")
    if warnings:
        lines.append(f"⚠️ {' | '.join(warnings)}")

    lines.append(f"📊 RSI: {sig.get('rsi', '?')} | ADX: {sig.get('adx', '?')}")
    lines.append(f"📈 ATR: {sig.get('atr', '?')}")
    lines.append(f"🕐 {sig.get('time', '?')}")
    
    reason = sig.get("reason", "")
    if reason:
        if len(reason) > 50:
            reason = reason[:47] + "..."
        lines.append(f"📝 {reason}")

    return "\n".join(lines)


def format_win_message(trade: dict) -> str:
    """پیام بسته شدن معامله با سود (WIN)"""
    tf = trade.get("timeframe", "5min").replace("min", "M")
    strategy = trade.get("strategy", "RANGE")
    pnl = trade.get("pnl", 0)
    pnl_str = f"+{pnl}" if pnl >= 0 else str(pnl)
    signal_id = trade.get("signal_id", "N/A")
    
    strategy_name = _get_strategy_name(strategy)

    return (
        f"🏆 <b>GOLD {trade['side']} — WIN</b> ({tf})\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 کد سیگنال: <b>{signal_id}</b>\n"
        f"🎯 استراتژی: <b>{strategy_name}</b>\n"
        f"💵 Entry: {trade.get('entry')}\n"
        f"🏁 Exit: {trade.get('exit_price')}\n"
        f"💰 سود: <b>{pnl_str}</b>\n"
        f"🕐 {trade.get('exit_time', '')}"
    )


def format_loss_message(trade: dict) -> str:
    """پیام بسته شدن معامله با ضرر (LOSS)"""
    tf = trade.get("timeframe", "5min").replace("min", "M")
    strategy = trade.get("strategy", "RANGE")
    pnl = trade.get("pnl", 0)
    pnl_str = f"+{pnl}" if pnl > 0 else str(pnl)
    signal_id = trade.get("signal_id", "N/A")
    
    strategy_name = _get_strategy_name(strategy)

    return (
        f"❌ <b>GOLD {trade['side']} — LOSS</b> ({tf})\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 کد سیگنال: <b>{signal_id}</b>\n"
        f"🎯 استراتژی: <b>{strategy_name}</b>\n"
        f"💵 Entry: {trade.get('entry')}\n"
        f"🏁 Exit: {trade.get('exit_price')}\n"
        f"💰 ضرر: <b>{pnl_str}</b>\n"
        f"🕐 {trade.get('exit_time', '')}"
    )


def _dashboard_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📊 مشاهده در داشبورد", "url": DASHBOARD_URL}]
        ]
    }


def send_telegram(text: str, with_dashboard_button: bool = False) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Telegram credentials missing")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if with_dashboard_button:
        payload["reply_markup"] = _dashboard_keyboard()

    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print(f"[!] Telegram error: {r.text}")
            return False
        return True
    except Exception as e:
        print(f"[!] Telegram exception: {e}")
        return False