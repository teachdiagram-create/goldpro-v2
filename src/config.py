import os
import sys


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"❌ Missing required secret: {name}")
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

# ══════════════════════════════════════════════════════════════
#  SL/TP — نسخه اصلاح‌شده  (R:R ≥ 1.5)
# ══════════════════════════════════════════════════════════════
SL_ATR_MULT = 1.0          # حداقل فاصله SL از entry (ضریب ATR)
TP_ATR_MULT = 2.5          # فاصله TP (ضریب ATR)
SL_STRUCTURE_BUFFER = 0.5  # بافر روی recent_high/low

# محدوده مجاز ATR (دلار) — زیر = بازار مرده، بالا = نوسان خطرناک
ATR_MIN_USD = 1.0
ATR_MAX_USD = 4.0

# حداقل فاصله مطلق SL/TP (دلار)
MIN_SL_USD = 3.0
MIN_TP_USD = 4.5

# ══════════════════════════════════════════════════════════════
#  ساعت‌های ممنوع (UTC)
#  بر اساس آمار داشبورد: ساعت 02:00 = -12.5 ❌
# ══════════════════════════════════════════════════════════════
BLOCKED_HOURS_UTC = [1, 2, 3]   # آسیا — ATR مرده، stop-hunt

# ══════════════════════════════════════════════════════════════
#  Cooldown
# ══════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════
#  Helper functions (مشترک بین signal_logic و mt5_trader)
# ══════════════════════════════════════════════════════════════
def compute_atr_effective(atr_raw: float) -> float:
    """
    ATR را در محدوده مجاز clamp می‌کند.
    برمی‌گرداند 0 اگر بازار مرده باشد.
    """
    if atr_raw is None or atr_raw <= 0:
        return 0.0
    if atr_raw < ATR_MIN_USD:
        return 0.0
    return min(atr_raw, ATR_MAX_USD)


def compute_sl_tp(side: str, price: float, atr: float,
                  recent_high: float = None, recent_low: float = None):
    """
    محاسبه SL/TP.

    منطق SL:
      SELL: max(recent_high + buffer*ATR, price + SL_ATR_MULT*ATR)
      BUY : min(recent_low  - buffer*ATR, price - SL_ATR_MULT*ATR)
      + حداقل مطلق MIN_SL_USD

    منطق TP:
      TP = max(TP_ATR_MULT * ATR, MIN_TP_USD)

    Returns:
      (sl, tp, sl_dist, tp_dist, rr) یا (None, None, None, None, None)
    """
    if atr is None or atr <= 0 or price is None or price <= 0:
        return None, None, None, None, None

    # ── SL ──
    if side == "SELL":
        sl_structure = (recent_high + SL_STRUCTURE_BUFFER * atr
                        if recent_high else price + MIN_SL_USD)
        sl_atr = price + SL_ATR_MULT * atr
        sl = max(sl_structure, sl_atr)
        if (sl - price) < MIN_SL_USD:
            sl = price + MIN_SL_USD
        sl_dist = sl - price
    elif side == "BUY":
        sl_structure = (recent_low - SL_STRUCTURE_BUFFER * atr
                        if recent_low else price - MIN_SL_USD)
        sl_atr = price - SL_ATR_MULT * atr
        sl = min(sl_structure, sl_atr)
        if (price - sl) < MIN_SL_USD:
            sl = price - MIN_SL_USD
        sl_dist = price - sl
    else:
        return None, None, None, None, None

    # ── TP ──
    tp_dist = max(TP_ATR_MULT * atr, MIN_TP_USD)
    if side == "BUY":
        tp = price + tp_dist
    else:
        tp = price - tp_dist

    # ── اعتبارسنجی نهایی ──
    rr = tp_dist / sl_dist if sl_dist > 0 else 0
    if rr < 1.0:
        return None, None, None, None, None

    return (round(sl, 2), round(tp, 2),
            round(sl_dist, 2), round(tp_dist, 2), round(rr, 2))