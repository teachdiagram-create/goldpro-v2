"""
ارسال نوتیفیکیشن از طریق Ntfy.sh
"""
import requests
from src.config import NTFY_TOPIC, NTFY_ENABLED


NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"


def send_ntfy(title: str, message: str, priority: int = 4, tags: list = None):
    """ارسال نوتیفیکیشن به Ntfy"""
    if not NTFY_ENABLED:
        print("⏸ Ntfy disabled")
        return False

    try:
        headers = {
            "Priority": str(priority),
            "Content-Type": "text/plain; charset=utf-8",
        }

        # Ntfy برای UTF-8 باید از X-Title استفاده کنه
        if title:
            # Encode UTF-8 as latin-1 bytes (trick for requests)
            headers["X-Title"] = title.encode('utf-8').decode('latin-1')

        if tags:
            headers["Tags"] = ",".join(tags)

        r = requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=10
        )

        if r.status_code != 200:
            print(f"[!] Ntfy HTTP {r.status_code}: {r.text[:200]}")
            return False

        print(f"[Ntfy] Sent OK: {title[:40]}")
        return True

    except Exception as e:
        print(f"[!] Ntfy error: {e}")
        return False

def send_signal_ntfy(signal: dict):
    """ارسال سیگنال به Ntfy"""
    side = signal.get("side", "?")
    tf = signal.get("timeframe", "5min").replace("min", "M")

    if side == "BUY":
        emoji = "🟢"
        tags = ["green_circle", "chart_with_upwards_trend", "moneybag"]
    else:
        emoji = "🔴"
        tags = ["red_circle", "chart_with_downwards_trend", "moneybag"]

    title = f"{emoji} سیگنال {side} — {tf}"

    message = (
        f"📊 RSI: {signal.get('rsi', '?')} | ADX: {signal.get('adx', '?')}\n"
        f"📈 ATR: {signal.get('atr', '?')}\n"
        f"⏰ {signal.get('time', '?')}"
    )

    return send_ntfy(title, message, priority=5, tags=tags)


def send_win_ntfy(trade: dict):
    """ارسال نوتیف WIN"""
    pnl = trade.get("pnl", 0)
    side = trade.get("side", "?")
    tf = trade.get("timeframe", "?")

    title = f"🎉 WIN +{pnl:.2f}"
    message = f"معامله {side} در {tf} برنده شد!"

    return send_ntfy(title, message, priority=4, tags=["tada", "moneybag"])