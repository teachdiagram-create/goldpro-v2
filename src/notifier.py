"""
ارسال نوتیفیکیشن از طریق Ntfy.sh
"""
import requests
from email.header import Header
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
            "Title": str(Header(title, 'utf-8')),
            "Content-Type": "text/plain; charset=utf-8",
        }
        if tags:
            headers["Tags"] = ",".join(tags)

        r = requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=10
        )
        r.raise_for_status()
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
        f"💵 ورود: {signal.get('entry', '?')}\n"
        f"🛑 SL: {signal.get('sl', '?')}\n"
        f"🎯 TP: {signal.get('tp', '?')}\n"
        f"📊 RSI: {signal.get('rsi', '?')} | ADX: {signal.get('adx', '?')}\n"
        f"📈 ATR: {signal.get('atr', '?')}"
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