import json
import os
from datetime import datetime, timedelta
from src.config import STATE_FILE, SIGNAL_COOLDOWN_MIN


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def should_send(signal: dict, state: dict) -> bool:
    """جلوگیری از ارسال سیگنال تکراری هم‌جهت در بازه کوتاه"""
    last = state.get("last_signal")
    if not last:
        return True

    if last["side"] != signal["side"]:
        return True  # جهت تغییر کرده → ارسال کن

    last_time = datetime.fromisoformat(last["sent_at"])
    if datetime.utcnow() - last_time > timedelta(minutes=SIGNAL_COOLDOWN_MIN):
        return True

    return False


def mark_sent(signal: dict, state: dict) -> dict:
    state["last_signal"] = {
        "side": signal["side"],
        "sent_at": datetime.utcnow().isoformat(),
    }
    return state
