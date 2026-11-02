import requests
from src.config import NTFY_TOPIC, NTFY_ENABLED


def send_signal_ntfy(sig: dict) -> bool:
    """ارسال سیگنال جدید به Ntfy"""
    if not NTFY_ENABLED:
        return False

    strategy = sig.get("strategy", "RANGE")
    if strategy == "TREND": s_name = "📈 Trend"
    elif strategy == "CORRELATION": s_name = "📊 Correlation"
    elif strategy == "ICHIMOKU": s_name = "☁️ Ichimoku"
    else: s_name = "🔄 Range"

    emoji = "🟢" if sig["side"] == "BUY" else "🔴"
    title = f"{emoji} GOLD {sig['side']} — {s_name}"
    
    q = sig.get("quality", {})
    body = (
        f"Entry: {sig.get('entry')} | SL: {sig.get('sl')} | TP: {sig.get('tp')}\n"
        f"کیفیت: {q.get('score')}/100 ({q.get('grade')})"
    )

    try:
        r = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode('utf-8'),
            headers={"Title": title.encode('utf-8'), "Priority": "high", "Tags": "chart_with_upwards_trend"},
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


def send_trade_closed_ntfy(trade: dict) -> bool:
    """ارسال پیام بسته شدن معامله (چه WIN چه LOSS) به Ntfy"""
    if not NTFY_ENABLED:
        return False

    strategy = trade.get("strategy", "RANGE")
    if strategy == "TREND": s_name = "📈 Trend"
    elif strategy == "CORRELATION": s_name = "📊 Correlation"
    elif strategy == "ICHIMOKU": s_name = "☁️ Ichimoku"
    else: s_name = "🔄 Range"

    result = trade.get("result")
    pnl = trade.get("pnl", 0)
    
    if result == "WIN":
        emoji = "🏆"; title = f"WIN: GOLD {trade['side']} ({s_name})"
    else:
        emoji = "❌"; title = f"LOSS: GOLD {trade['side']} ({s_name})"

    body = (
        f"Entry: {trade.get('entry')} -> Exit: {trade.get('exit_price')}\n"
        f"سود/ضرر: {pnl:+.2f}"
    )

    try:
        r = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode('utf-8'),
            headers={"Title": title.encode('utf-8'), "Priority": "default", "Tags": "checkered_flag"},
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False