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

# ==== Signal filters ====
ADX_MIN = 15
RSI_BUY_MIN = 50
RSI_BUY_MAX = 70
RSI_SELL_MIN = 30
RSI_SELL_MAX = 50

# ==============================================================
#  SL/TP - Version 3 (ADX-aware)
# ==============================================================
SL_ATR_MULT = 1.5           # پایه (روند عادی)
TP_ATR_MULT = 2.5           # ثابت
SL_STRUCTURE_BUFFER = 1.0   # از 0.5 → 1.0

# ADX multiplier - روند قوی -> SL بازتر
ADX_STRONG_THRESHOLD = 40
ADX_SL_BOOST = 1.5          # ضریب اضافه وقتی ADX > 40

# محدوده ATR (دلار)
ATR_MIN_USD = 1.0
ATR_MAX_USD = 4.0

# حداقل فاصله مطلق (دلار)
MIN_SL_USD = 4.5
MIN_TP_USD = 6.5

# ==============================================================
#  ساعات ممنوع (UTC)
# ==============================================================
BLOCKED_HOURS_UTC = [1, 2, 3]

# ==== Cooldown ====
SIGNAL_COOLDOWN_MIN = 60

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
#  Helper functions
# ==============================================================
def compute_atr_effective(atr_raw: float) -> float:
    """ATR را clamp می‌کند. 0 = بازار مرده."""
    if atr_raw is None or atr_raw <= 0:
        return 0.0
    if atr_raw < ATR_MIN_USD:
        return 0.0
    return min(atr_raw, ATR_MAX_USD)


def get_sl_atr_mult(adx_value: float) -> float:
    """
    ضریب SL بر اساس قدرت روند (ADX).

    - ADX > 40  -> روند قوی  -> SL بازتر
    - ADX <= 40 -> روند عادی -> SL پایه
    """
    if adx_value is not None and adx_value > ADX_STRONG_THRESHOLD:
        return SL_ATR_MULT * ADX_SL_BOOST
    return SL_ATR_MULT


def compute_sl_tp(side: str, price: float, atr: float,
                  adx_value: float = None,
                  recent_high: float = None,
                  recent_low: float = None):
    """
    محاسبه SL/TP با در نظر گرفتن ADX.

    Returns:
        (sl, tp, sl_dist, tp_dist, rr) یا (None, None, None, None, None)
    """
    if atr is None or atr <= 0 or price is None or price <= 0:
        return None, None, None, None, None

    sl_mult = get_sl_atr_mult(adx_value)

    # --- SL ---
    if side == "SELL":
        sl_structure = (recent_high + SL_STRUCTURE_BUFFER * atr
                        if recent_high else price + MIN_SL_USD)
        sl_atr = price + sl_mult * atr
        sl = max(sl_structure, sl_atr)
        if (sl - price) < MIN_SL_USD:
            sl = price + MIN_SL_USD
        sl_dist = sl - price
    elif side == "BUY":
        sl_structure = (recent_low - SL_STRUCTURE_BUFFER * atr
                        if recent_low else price - MIN_SL_USD)
        sl_atr = price - sl_mult * atr
        sl = min(sl_structure, sl_atr)
        if (price - sl) < MIN_SL_USD:
            sl = price - MIN_SL_USD
        sl_dist = price - sl
    else:
        return None, None, None, None, None

    # --- TP ---
    tp_dist = max(TP_ATR_MULT * atr, MIN_TP_USD)
    if side == "BUY":
        tp = price + tp_dist
    else:
        tp = price - tp_dist

    # --- اعتبارسنجی ---
    rr = tp_dist / sl_dist if sl_dist > 0 else 0
    if rr < 1.0:
        return None, None, None, None, None

    return (round(sl, 2), round(tp, 2),
            round(sl_dist, 2), round(tp_dist, 2), round(rr, 2))