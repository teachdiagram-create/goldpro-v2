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
SYMBOL = "XAU/USD"
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

# ==============================================================
#  SL/TP - محدودیت‌دار
# ==============================================================
SL_ATR_MULT = 2.5
TP_ATR_MULT = 3.5
MIN_SL_USD = 3.0
MIN_TP_USD = 4.5

# ⚠️ حداکثر فاصله‌ی مجاز
MAX_SL_USD = 15.0
MAX_TP_USD = 21.0

# ==============================================================
#  Quality Filter — فقط اینا ارسال می‌شن
# ==============================================================
ALLOWED_GRADES = ["A", "B"]   # ← C و D اصلاً فرستاده نمی‌شن

# ==============================================================
#  Risk Management
# ==============================================================
MAX_OPEN_TRADES = 1       # حداکثر ۱ ترید باز در هر زمان
SIGNAL_COOLDOWN_MIN = 60  # حداقل ۶۰ دقیقه بین دو سیگنال

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
#  Helper: SL/TP Calculator (با Limit)
# ==============================================================
def compute_sl_tp(side: str, price: float, atr: float):
    if atr is None or atr <= 0 or price is None or price <= 0:
        return None, None, None, None, None

    sl_dist = max(SL_ATR_MULT * atr, MIN_SL_USD)
    tp_dist = max(TP_ATR_MULT * atr, MIN_TP_USD)

    # 🚨 اعمال سقف
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

# ==============================================================
#  استراتژی جدید: Correlation + Trend
# ==============================================================
SL_CORR_MULT = 1.0     # SL = 1.0 × ATR (طبق درخواستت)
TP_CORR_MULT = 1.5     # TP = 1.5 × ATR (طبق درخواستت)
DXY_SYMBOL = "DXY"     # نماد شاخص دلار در TwelveData