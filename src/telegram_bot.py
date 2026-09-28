import requests
from src.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def _emoji(side: str) -> str:
    return "🟢" if side == "BUY" else "🔴"


def format_message(sig: dict) -> str:
    tf = sig.get("timeframe", "5min").replace("min", "M")
    return (
        f"{_emoji(sig['side'])} <b>GOLD {sig['side']} — {tf}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💵 Entry: <b>{sig['entry']}</b>\n"
        f"🛑 SL: {sig['sl']}\n"
        f"🎯 TP: {sig['tp']}\n"
        f"📊 RSI: {sig.get('rsi', 'N/A')} | ADX: {sig.get('adx', 'N/A')}\n"
        f"📈 ATR: {sig.get('atr', 'N/A')}\n"
        f"⏰ {sig.get('time', 'N/A')} UTC"
    )


def send_telegram(text: str) -> bool:
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

    r = requests.post(url, data=payload, timeout=15)
    if r.status_code != 200:
        print(f"[!] Telegram error: {r.text}")
        return False
    return True