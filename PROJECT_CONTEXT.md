# GoldPro V2 — Project Context

## Owner: روح‌اله

## Architecture
- GitHub Actions → Python bot → Telegram/Ntfy/SMS
- MT5 trader on PC
- PWA dashboard (docs/)
- State in Gist

## Key files
- src/config.py       ← همه‌ی تنظیمات
- src/indicators.py   ← EMA/RSI/ATR/ADX/MACD
- src/strategy.py     ← Double Top/Bottom تشخیص
- src/signal_logic.py ← تولید سیگنال + SL/TP
- mt5_trader.py       ← اجرای معامله

## Decision log
- 1405/07/21 — SL/TP بازنویسی شد: R:R از 0.75 → 1.5
- ATR از هر دو 5min و 15min میاد (بزرگ‌تر)
- بلاک ساعات 01-03 UTC (بازار آسیا، -12.5 داد)
- mt5_trader.py فقط consumer سیگناله، SL/TP رو از سیگنال می‌گیره

## Current stats
- 12 signal, 8W/4L, WR 66.7%, PF 2.0, DD -11.56

## TODO
- [ ] بک‌تست ضرایب جدید
- [ ] لاگ ATR بعد 30 trade
- [ ] شاید MAX_BARS_SINCE_PEAK = 3 بشه