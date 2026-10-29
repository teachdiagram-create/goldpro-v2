import os
import sys


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"Missing required secret: {name}")
        sys.exit(1)
    return val


# ==== Secrets ====
TELEGRAM_TOKEN = _require("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = _require("TELEGRAM_CHAT_ID")
TWELVEDATA_KEY = _require("TWELVEDATA_KEY")

GH_GIST_ID = os.getenv("GH_GIST_ID", "").strip()
GH_PAT = os.getenv("GH_PAT", "").strip()
USE_GIST = bool(GH_GIST_ID and GH_PAT)

# ==== Market ====
# ==== Market ====
SYMBOL = "XAU/USD"
DXY_SYMBOL = "DX-Y.NYB"  
OUTPUT_SIZE = 200
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

# ==== Signal filters ====
ADX_MIN = 15
RSI_BUY_MIN = 50
RSI_BUY_MAX = 70
RSI_SELL_MIN = 30
RSI_SELL_MAX = 50

# ==============================================================
#  SL/TP - تنظیمات اصلاح‌شده برای تایم‌فریم ۵ دقیقه
# ==============================================================
SL_ATR_MULT = 2.5
TP_ATR_MULT = 2.5   # ← TP قابل دسترس‌تر
MIN_SL_USD = 3.0
MIN_TP_USD = 4.5

# ⚠️ سقف مطلق (برای جلوگیری از TP/SL های خیلی دور)
MAX_SL_USD = 12.0
MAX_TP_USD = 15.0

# استراتژی Correlation (همبستگی)
SL_CORR_MULT = 1.0
TP_CORR_MULT = 1.5
# ==============================================================
#  استراتژی ایچیموکو
# ==============================================================
SL_ICHI_MULT = 1.5   # SL: 1.5 برابر ATR
TP_ICHI_MULT = 2.5   # TP: 2.5 برابر ATR

# ==============================================================
#  Quality Filter
# ==============================================================
ALLOWED_GRADES = ["A", "B"]

# ==============================================================
#  Risk Management
# ==============================================================
MAX_OPEN_TRADES = 1
SIGNAL_COOLDOWN_MIN = 60

# ==== Trade Tracking ====
TRADE_CHECK_MAX_BARS = 200   # حداکثر کندلی که برای چک کردن SL/TP بررسی می‌شه

# ==== Ntfy ====
NTFY_TOPIC = "goldpro_roohollah_2026"
NTFY_ENABLED = True

# ==== SMS.ir ====
SMSIR_API_KEY = os.getenv("SMSIR_API_KEY", "").strip()
SMSIR_LINE_NUMBER = os.getenv("SMSIR_LINE_NUMBER", "").strip()
SMSIR_PHONE = os.getenv("SMSIR_PHONE", "").strip()
SMS_ENABLED = bool(SMSIR_API_KEY and SMSIR_LINE_NUMBER and SMSIR_PHONE)

# ==== State ====
STATE_FILE = "state.json"

# ==== Dashboard ====
DASHBOARD_URL = "https://teachdiagram-create.github.io/goldpro-v2/"


# ==============================================================
#  Helper: SL/TP Calculator (با سقف مطلق)
# ==============================================================
def compute_sl_tp(side: str, price: float, atr: float):
    if atr is None or atr <= 0 or price is None or price <= 0:
        return None, None, None, None, None

    sl_dist = max(SL_ATR_MULT * atr, MIN_SL_USD)
    tp_dist = max(TP_ATR_MULT * atr, MIN_TP_USD)

    # 🚨 اعمال سقف مطلق
    sl_dist = min(sl_dist, MAX_SL_USD)
    tp_dist = min(tp_dist, MAX_TP_USD)

    if side == "SELL":
        sl = round(price + sl_dist, 2)
        tp = round(price - tp_dist, 2)
    elif side == "BUY":
        sl = round(price - sl_dist, 2)
        tp = round(price + tp_dist, 2)
    else:
        return None, None, None, None, None

    rr = tp_dist / sl_dist if sl_dist > 0 else 0
    return (sl, tp, round(sl_dist, 2), round(tp_dist, 2), round(rr, 2))