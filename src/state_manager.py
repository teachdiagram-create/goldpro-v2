import json
import requests
from datetime import datetime, timedelta
from src.config import GH_GIST_ID, GH_PAT, SIGNAL_COOLDOWN_MIN


GIST_API = f"https://api.github.com/gists/{GH_GIST_ID}"
MAX_HISTORY = 200


def _headers():
    return {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _symbol_of(signal_or_trade: dict) -> str:
    return signal_or_trade.get("symbol", "XAU/USD")


def _key(signal_or_trade: dict) -> str:
    """کلید یکتا برای cooldown: SYMBOL:TF:SIDE:STRATEGY"""
    symbol = _symbol_of(signal_or_trade)
    tf = signal_or_trade.get("timeframe", "5min")
    side = signal_or_trade.get("side")
    strategy = signal_or_trade.get("strategy", "RANGE")
    return f"{symbol}:{tf}:{side}:{strategy}"


def load_state() -> dict:
    try:
        r = requests.get(GIST_API, headers=_headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        files = data.get("files", {})
        if "goldpro-state.json" not in files:
            return {"last_signals": {}, "history": []}

        content = files["goldpro-state.json"].get("content", "{}")
        state = json.loads(content) if content.strip() else {}

        if "last_signals" not in state:
            old = {k: v for k, v in state.items() if ":" in k}
            return {"last_signals": old, "history": []}

        state.setdefault("history", [])
        return state
    except Exception as e:
        print(f"[!] load_state error: {e}")
        return {"last_signals": {}, "history": []}


def save_state(state: dict) -> bool:
    try:
        payload = {
            "files": {
                "goldpro-state.json": {
                    "content": json.dumps(state, indent=2, ensure_ascii=False)
                }
            }
        }
        r = requests.patch(GIST_API, headers=_headers(), json=payload, timeout=20)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[!] save_state error: {e}")
        return False


def should_send(signal: dict, state: dict) -> bool:
    key = _key(signal)
    tf = signal.get("timeframe", "5min")
    strategy = signal.get("strategy", "RANGE")

    last = state.get("last_signals", {}).get(key)
    if not last:
        return True

    last_time = datetime.fromisoformat(last["sent_at"])
    elapsed = datetime.utcnow() - last_time

    if elapsed > timedelta(minutes=SIGNAL_COOLDOWN_MIN):
        return True

    remaining = SIGNAL_COOLDOWN_MIN - int(elapsed.total_seconds() / 60)
    print(f"⏸ Cooldown {strategy} {tf} — {remaining} min remaining")
    return False


def mark_sent(signal: dict, state: dict) -> dict:
    key = _key(signal)
    symbol = _symbol_of(signal)
    tf = signal.get("timeframe", "5min")
    strategy = signal.get("strategy", "RANGE")
    now = datetime.utcnow().isoformat()

    state.setdefault("last_signals", {})
    state.setdefault("history", [])

    state["last_signals"][key] = {
        "symbol": symbol,
        "side": signal["side"],
        "timeframe": tf,
        "strategy": strategy,
        "sent_at": now,
        "entry": signal["entry"],
    }

    # ثبت کامل ترید در تاریخچه
    new_trade = {
        "signal_id": signal.get("signal_id", "N/A"),   # ← شناسه منحصر به فرد
        "symbol": symbol,
        "side": signal["side"],
        "timeframe": tf,
        "strategy": strategy,
        "quality": signal.get("quality"),
        "entry": signal["entry"],
        "sl": signal.get("sl"),
        "tp": signal.get("tp"),
        "sl_distance": signal.get("sl_distance"),
        "tp_distance": signal.get("tp_distance"),
        "rr": signal.get("rr"),
        "rsi": signal.get("rsi"),
        "adx": signal.get("adx"),
        "atr": signal.get("atr"),
        "reason": signal.get("reason"),
        "sent_at": now,
        "result": None,
        "exit_price": None,
        "exit_time": None,
        "pnl": None,
    }

    state["history"].insert(0, new_trade)
    state["history"] = state["history"][:MAX_HISTORY]

    # پاک کردن سیگنال‌های قدیمی‌تر از ۲۴ ساعت
    cutoff = datetime.utcnow() - timedelta(hours=24)
    state["last_signals"] = {
        k: v for k, v in state["last_signals"].items()
        if datetime.fromisoformat(v["sent_at"]) > cutoff
    }

    return state