import os

# ==== Telegram ====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ==== Data API (TwelveData) ====
TWELVEDATA_KEY = os.getenv("TWELVEDATA_KEY", "")
SYMBOL = "XAU/USD"
INTERVAL = "5min"
OUTPUT_SIZE = 200  # تعداد کندل برای محاسبه اندیکاتورها

# ==== Indicator Settings ====
EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ADX_PERIOD = 14
ATR_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ==== Signal Rules ====
ADX_MIN = 25          # حداقل قدرت روند
RSI_BUY_MIN = 50
RSI_BUY_MAX = 70
RSI_SELL_MIN = 30
RSI_SELL_MAX = 50

# ==== Risk Management (ATR based) ====
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.0

# ==== Anti-Spam ====
SIGNAL_COOLDOWN_MIN = 30   # حداقل فاصله بین دو سیگنال هم‌جهت (دقیقه)

# ==== State File ====
STATE_FILE = "state.json"
