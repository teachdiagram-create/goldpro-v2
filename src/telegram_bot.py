import requests
from src.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DASHBOARD_URL


def _emoji(side: str) -> str:
    return "🟢" if side == "BUY" else "🔴"


def format_message(sig: dict) -> str:
    tf = sig.get("timeframe", "5min").replace("min", "M")

    # محاسبه R:R
    rr_text = ""
    if sig.get("entry") and sig.get("sl") and sig.get("tp"):
        risk = abs(sig["entry"] - sig["sl"])
        reward = abs(sig["tp"] - sig["entry"])
        if risk > 0:
            rr_text = f"\n⚖️ R:R = 1 : {reward / risk:.2f}"

    return (
        f"{_emoji(sig['side'])} <b>GOLD {sig['side']} — {tf}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💵 Entry: <b>{sig['entry']}</b>\n"
        f"🛑 SL: {sig['sl']}\n"
        f"🎯 TP: {sig['tp']}"
        f"{rr_text}\n"
        f"📊 RSI: {sig.get('rsi', 'N/A')} | ADX: {sig.get('adx', 'N/A')}\n"
        f"📈 ATR: {sig.get('atr', 'N/A')}\n"
        f"⏰ {sig.get('time', 'N/A')} UTC"
    )


def _dashboard_keyboard():
    """دکمه‌های inline برای تلگرام"""
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