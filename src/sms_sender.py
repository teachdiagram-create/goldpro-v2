"""
ارسال SMS از طریق SMS.ir
"""
import requests
from src.config import SMSIR_API_KEY, SMSIR_LINE_NUMBER, SMSIR_PHONE, SMS_ENABLED


SMSIR_URL = "https://api.sms.ir/v1/send/bulk"


def send_sms(message: str) -> bool:
    """ارسال SMS به شماره مشخص"""
    if not SMS_ENABLED:
        print("⏸ SMS disabled")
        return False

    if not SMSIR_API_KEY or not SMSIR_LINE_NUMBER or not SMSIR_PHONE:
        print("[!] SMS credentials missing")
        return False

    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": SMSIR_API_KEY,
        }

        payload = {
            "lineNumber": SMSIR_LINE_NUMBER,
            "messageText": message,
            "mobiles": [SMSIR_PHONE],
        }

        r = requests.post(SMSIR_URL, json=payload, headers=headers, timeout=15)

        if r.status_code != 200:
            print(f"[!] SMS HTTP {r.status_code}: {r.text[:200]}")
            return False

        data = r.json()
        if data.get("status") == 1:
            print(f"[SMS] Sent OK")
            return True
        else:
            print(f"[!] SMS error: {data}")
            return False

    except Exception as e:
        print(f"[!] SMS exception: {e}")
        return False


def send_signal_sms(signal: dict):
    """SMS سیگنال جدید"""
    side = signal.get("side", "?")
    tf = signal.get("timeframe", "5min").replace("min", "M")
    emoji = "🟢" if side == "BUY" else "🔴"

    message = (
        f"{emoji} GoldPro: {side} {tf}\n"
        f"RSI: {signal.get('rsi', '?')} | ADX: {signal.get('adx', '?')}\n"
        f"ATR: {signal.get('atr', '?')}"
    )

    return send_sms(message)


def send_win_sms(trade: dict):
    """SMS برد"""
    pnl = trade.get("pnl", 0)
    side = trade.get("side", "?")
    tf = trade.get("timeframe", "?")

    message = f"🎉 GoldPro WIN: +{pnl:.2f}\n{side} در {tf} برنده شد!"

    return send_sms(message)