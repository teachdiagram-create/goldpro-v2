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


def load_state() -> dict:
    """خواندن state از Gist"""
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
    """ذخیره state در Gist"""
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
    """چک کن که آیا این سیگنال رو باید بفرستیم یا نه"""
    tf = signal.get("timeframe", "5min")
    strategy = signal.get("strategy", "RANGE")
    # کلید رو با استراتژی جدا می‌کنیم تا کول‌داون هر استراتژی مستقل باشه
    key = f"{tf}:{signal['side']}:{strategy}"

    last = state.get("last_signals", {}).get(key)
    if not last:
        return True

    last_time = datetime.fromisoformat(last["sent_at"])
    elapsed = datetime.utcnow() - last_time

    if elapsed > timedelta(minutes=SIGNAL_COOLDOWN_MIN):
        return True

    remaining = SIGNAL_COOLDOWN_MIN - int(elapsed.total_seconds() / 60)
    print(f"⏸ Cooldown {strategy} {tf} {signal['side']} — {remaining} min remaining")
    return False


def mark_sent(signal: dict, state: dict) -> dict:
    """ثبت سیگنال ارسال‌شده در state + history"""
    tf = signal.get("timeframe", "5min")
    strategy = signal.get("strategy", "RANGE")
    key = f"{tf}:{signal['side']}:{strategy}"
    now = datetime.utcnow().isoformat()

    state.setdefault("last_signals", {})
    state.setdefault("history", [])

    state["last_signals"][key] = {
        "side": signal["side"],
        "timeframe": tf,
        "strategy": strategy,
        "sent_at": now,
        "entry": signal["entry"],
    }

    # 🚨 اینجا استراتژی و کیفیت هم به تاریخچه اضافه می‌شن
    new_trade = {
        "side": signal["side"],
        "timeframe": tf,
        "strategy": strategy,               # ← اضافه شد
        "quality": signal.get("quality"),   # ← اضافه شد
        "entry": signal["entry"],
        "sl": signal.get("sl"),
        "tp": signal.get("tp"),
        "rsi": signal.get("rsi"),
        "adx": signal.get("adx"),
        "atr": signal.get("atr"),
        "reason": signal.get("reason"),
        "rr": signal.get("rr"),
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