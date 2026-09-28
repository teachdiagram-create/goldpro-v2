from src.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from src.telegram_bot import send_telegram

msg = (
    "🧪 <b>GoldPro V2 — Test</b>\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "اگه این پیام رو می‌بینی، یعنی تلگرام درست ست شده ✅"
)

ok = send_telegram(msg)
print("Sent!" if ok else "Failed!")