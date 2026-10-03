import os
import sys


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"❌ Missing required secret: {name}")
        sys.exit(1)
    return val


TELEGRAM_TOKEN = _require("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = _require("TELEGRAM_CHAT_ID")
TWELVEDATA_KEY = _require("TWELVEDATA_KEY")

GH_GIST_ID = os.getenv("GH_GIST_ID", "").strip()
GH_PAT = os.getenv("GH_PAT", "").strip()
USE_GIST = bool(GH_GIST_ID and GH_PAT)

SYMBOL = "XAU/USD"
OUTPUT_SIZE = 200

TIMEFRAMES = ["1min", "5min", "15min"]

EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ADX_PERIOD = 14
ATR_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

ADX_MIN = 15
RSI_BUY_MIN = 50
RSI_BUY_MAX = 70
RSI_SELL_MIN = 30
RSI_SELL_MAX = 50

SL_ATR_MULT = 2.5
TP_ATR_MULT = 1.5

SIGNAL_COOLDOWN_MIN = 60
# ==== Ntfy ====
NTFY_TOPIC = "goldpro_roohollah_2026"
NTFY_ENABLED = True
# ==== SMS.ir ====
SMSIR_API_KEY = os.getenv("SMSIR_API_KEY", "").strip()
SMSIR_LINE_NUMBER = os.getenv("SMSIR_LINE_NUMBER", "").strip()
SMSIR_PHONE = os.getenv("SMSIR_PHONE", "").strip()
SMS_ENABLED = bool(SMSIR_API_KEY and SMSIR_LINE_NUMBER and SMSIR_PHONE)

STATE_FILE = "state.json"

# ==== Dashboard ====
DASHBOARD_URL = "https://teachdiagram-create.github.io/goldpro-v2/"