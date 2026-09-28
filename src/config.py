import os
import sys


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"❌ Missing required secret: {name}")
        sys.exit(1)
    return val


# ==== Secrets (اجباری) ====
TELEGRAM_TOKEN = _require("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = _require("TELEGRAM_CHAT_ID")
TWELVEDATA_KEY = _require("TWELVEDATA_KEY")

# ==== Optional (فقط اگه Gist داری) ====
GH_GIST_ID = os.getenv("GH_GIST_ID", "").strip()
GH_PAT = os.getenv("GH_PAT", "").strip()
USE_GIST = bool(GH_GIST_ID and GH_PAT)

# ==== Data API ====
SYMBOL = "XAU/USD"
OUTPUT_SIZE = 200

# ==== Timeframes ====
TIMEFRAMES = ["5min", "15min"]

# ==== Indicators ====
EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ADX_PERIOD = 14
ATR_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ==== Signal Rules ====
ADX_MIN = 25
RSI_BUY_MIN = 50
RSI_BUY_MAX = 70
RSI_SELL_MIN = 30
RSI_SELL_MAX = 50

# ==== Risk Management ====
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.0

# ==== Anti-Spam ====
SIGNAL_COOLDOWN_MIN = 60

# ==== State ====
STATE_FILE = "state.json"