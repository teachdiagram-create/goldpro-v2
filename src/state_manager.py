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
    """خواندن state از Gist (با پشتیبانی از فرمت قدیمی)"""
    try:
        r = requests.get(GIST_API, headers=_headers(), timeout=20)
        r.raise_for_status()
        data = r.json()
        files = data.get("files", {})
        if "goldpro-state.json" not in files:
            return {"last_signals": {}, "history": []}

        content = files["goldpro-state.json"].get("content", "{}")
        state = json.loads(content) if content.strip() else {}

        # Backward compatibility
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
    key = f"{tf}:{signal['side']}"

    last = state.get("last_signals", {}).get(key)
    if not last:
        return True

    last_time = datetime.fromisoformat(last["sent_at"])
    elapsed = datetime.utcnow() - last_time

    if elapsed > timedelta(minutes=SIGNAL_COOLDOWN_MIN):
        return True

    remaining = SIGNAL_COOLDOWN_MIN - int(elapsed.total_seconds() / 60)
    print(f"⏸ Cooldown {tf} {signal['side']} — {remaining} min remaining")
    return False


def mark_sent(signal: dict, state: dict) -> dict:
    """ثبت سیگنال ارسال‌شده در state + history"""
    tf = signal.get("timeframe", "5min")
    key = f"{tf}:{signal['side']}"
    now = datetime.utcnow().isoformat()

    state.setdefault("last_signals", {})
    state.setdefault("history", [])

    # به‌روزرسانی آخرین سیگنال
    state["last_signals"][key] = {
        "side": signal["side"],
        "timeframe": tf,
        "sent_at": now,
        "entry": signal["entry"],
    }

    # اضافه به history
    state["history"].insert(0, {
        "side": signal["side"],
        "timeframe": tf,
        "entry": signal["entry"],
        "sl": signal.get("sl"),
        "tp": signal.get("tp"),
        "rsi": signal.get("rsi"),
        "adx": signal.get("adx"),
        "atr": signal.get("atr"),
        "sent_at": now,
    })

    # فقط ۲۰۰ تای آخر
    state["history"] = state["history"][:MAX_HISTORY]

    # پاک‌سازی last_signals قدیمی (بیشتر از ۲۴ ساعت)
    cutoff = datetime.utcnow() - timedelta(hours=24)
    state["last_signals"] = {
        k: v for k, v in state["last_signals"].items()
        if datetime.fromisoformat(v["sent_at"]) > cutoff
    }

    return state