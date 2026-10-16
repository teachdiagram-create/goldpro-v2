import requests
from src.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DASHBOARD_URL


def _emoji(side: str) -> str:
    return "🟢" if side == "BUY" else "🔴"


def _grade_emoji(grade: str) -> str:
    return {"A": "🏆", "B": "✅", "C": "⚠️", "D": "🚫"}.get(grade, "❔")


def format_message(sig: dict) -> str:
    tf = sig.get("timeframe", "5min").replace("min", "M")
    entry = sig.get("entry", "?")
    sl = sig.get("sl", "?")
    tp = sig.get("tp", "?")

    # ── R:R ──
    rr_text = ""
    if sig.get("rr") is not None:
        rr_text = f"⚖️ R:R = 1 : {sig['rr']:.2f}"

    # ── SL/TP ──
    sl_line = f"🛑 SL: {sl}"
    tp_line = f"🎯 TP: {tp}"
    if sig.get("sl_distance") is not None:
        sl_line += f"  <i>({sig['sl_distance']})</i>"
    if sig.get("tp_distance") is not None:
        tp_line += f"  <i>({sig['tp_distance']})</i>"

    # ── کیفیت ──
    q = sig.get("quality") or {}
    score = q.get("score", 0)
    grade = q.get("grade", "?")
    flags = q.get("flags", [])
    warnings = q.get("warnings", [])

    quality_line = f"⭐ کیفیت: <b>{score}/100</b>  {_grade_emoji(grade)} <b>{grade}</b>"

    lines = [
        f"{_emoji(sig['side'])} <b>GOLD {sig['side']} — {tf}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"💵 Entry: <b>{entry}</b>",
        sl_line,
        tp_line,
    ]
    if rr_text:
        lines.append(rr_text)
    lines.append(quality_line)

    if flags:
        lines.append(f"✅ {' | '.join(flags)}")
    if warnings:
        lines.append(f"⚠️ {' | '.join(warnings)}")

    lines.append(f"📊 RSI: {sig.get('rsi', '?')} | ADX: {sig.get('adx', '?')}")
    lines.append(f"📈 ATR: {sig.get('atr', '?')}")
    lines.append(f"🕐 {sig.get('time', '?')}")

    return "\n".join(lines)


def _dashboard_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📊 مشاهده در داشبورد", "url": DASHBOARD_URL}]
        ]
    }


def send_telegram(text: str, with_dashboard_button: bool = True) -> bool:
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