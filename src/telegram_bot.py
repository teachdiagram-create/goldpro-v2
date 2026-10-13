import requests
from src.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DASHBOARD_URL


def _emoji(side: str) -> str:
    return "🟢" if side == "BUY" else "🔴"


def _trend_badge(sig: dict) -> str:
    """نشون‌دهنده‌ی قدرت روند."""
    if sig.get("strong_trend"):
        return "🔥 STRONG"
    return ""


def format_message(sig: dict) -> str:
    tf = sig.get("timeframe", "5min").replace("min", "M")
    entry = sig.get("entry", "?")
    sl = sig.get("sl", "?")
    tp = sig.get("tp", "?")

    # --- R:R ---
    rr_text = ""
    try:
        if entry and sl and tp:
            risk = abs(float(entry) - float(sl))
            reward = abs(float(tp) - float(entry))
            if risk > 0:
                rr_text = f"⚖️ R:R = 1 : {reward / risk:.2f}"
    except Exception:
        pass

    # --- SL/TP distances (اگه تو سیگنال باشه) ---
    sl_dist = sig.get("sl_distance")
    tp_dist = sig.get("tp_distance")
    sl_line = f"🛑 SL: {sl}"
    tp_line = f"🎯 TP: {tp}"
    if sl_dist is not None:
        sl_line += f"  <i>({sl_dist})</i>"
    if tp_dist is not None:
        tp_line += f"  <i>({tp_dist})</i>"

    # --- ADX badge ---
    adx_val = sig.get("adx", "N/A")
    trend_badge = _trend_badge(sig)
    adx_line = f"📊 RSI: {sig.get('rsi', 'N/A')} | ADX: {adx_val}"
    if trend_badge:
        adx_line += f"  {trend_badge}"

    # --- SL multiplier ---
    sl_mult = sig.get("sl_mult")
    atr_val = sig.get("atr", "N/A")
    atr_line = f"📈 ATR: {atr_val}"
    if sl_mult is not None:
        atr_line += f" | SL mult: {sl_mult}x"

    lines = [
        f"{_emoji(sig['side'])} <b>GOLD {sig['side']} — {tf}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"💵 Entry: <b>{entry}</b>",
        sl_line,
        tp_line,
    ]
    if rr_text:
        lines.append(rr_text)
    lines.append(adx_line)
    lines.append(atr_line)
    lines.append(f"⏰ {sig.get('time', 'N/A')} UTC")

    return "\n".join(lines)


def _dashboard_keyboard():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "📊 مشاهده در داشبورد",
                    "url": DASHBOARD_URL,
                }
            ]
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