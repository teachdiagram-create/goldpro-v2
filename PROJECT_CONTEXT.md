# GoldPro V2 — Context

## Owner
روح‌اله

## Architecture
- GitHub Actions → main.py → signal_logic → Telegram/Ntfy/SMS
- State در Gist (GH_GIST_ID + GH_PAT)
- PC listener از Gist می‌خونه → mt5_trader.open_trade(signal)
- PWA dashboard در docs/ (GitHub Pages)

## File map
- src/config.py        — همه‌ی تنظیمات + helper های SL/TP
- src/indicators.py    — EMA/RSI/ATR/ADX/MACD (ATR با ewm، استاندارد)
- src/strategy.py      — detect_double_top_sell / detect_double_bottom_buy
- src/signal_logic.py  — evaluate_signal (تولید سیگنال + SL/TP)
- src/telegram_bot.py  — format_message + send_telegram
- src/notifier.py      — Ntfy
- src/sms_sender.py    — SMS.ir
- src/state_manager.py — Gist read/write
- src/trade_tracker.py — پیگیری تریدهای باز + محاسبه آمار
- mt5_trader.py        — اجرای معامله (on PC)
- main.py              — entry point (GitHub Actions)

## Strategies
- RSI Double Top (SELL) / Double Bottom (BUY)
- lookback=50, threshold=70/30, max_bars_since_peak=2, min_decline=1.0
- ADX_MIN = 15 (فیلتر روند ضعیف)

## History of SL/TP
- v1: SL=4×ATR, TP=3×ATR → R:R=0.75 ❌ (SL < TP اشتباه)
- v2: SL=1.0×ATR, TP=2.5×ATR, MIN_SL=3 → R:R=2.5
      مشکل: SL=3.11 دلار خورد، بازار برگشت → SL تنگ بود
- v3 (فعلی): ADX-aware
      - ADX ≤ 40 → SL = 1.5 × ATR
      - ADX > 40 → SL = 2.25 × ATR
      - MIN_SL = 4.5, MIN_TP = 6.5

## Key settings (v3)
## Architecture rule
- برای تغییر استراتژی فقط src/strategy.py رو تغییر بده
- interface: detect_double_top_sell / detect_double_bottom_buy
- خروجی: dict با کلیدهای peak1_value, peak2_value, current_rsi
  (یا trough1_value, trough2_value برای BUY)
- بقیه‌ی فایل‌ها دست نمی‌خورن