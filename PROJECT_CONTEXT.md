# GoldPro V2 — Context

## Owner
روح‌اله

## Architecture
- GitHub Actions → main.py → signal_logic → Telegram/Ntfy/SMS
- State در Gist
- PC listener از Gist می‌خونه → mt5_trader.open_trade()
- PWA dashboard در docs/

## History of SL/TP
- v1: SL=4×ATR, TP=3×ATR → R:R=0.75 ❌
- v2: SL=1.0×ATR, TP=2.5×ATR, MIN_SL=3 → R:R=2.5 ولی SL تنگ
- v3 (فعلی): SL=1.5×ATR, ADX>40 → 2.25×ATR, MIN_SL=4.5

## Key settings (v3)
- SL_ATR_MULT = 1.5
- TP_ATR_MULT = 2.5
- ADX_STRONG_THRESHOLD = 40
- ADX_SL_BOOST = 1.5
- MIN_SL_USD = 4.5
- MIN_TP_USD = 6.5
- BLOCKED_HOURS_UTC = [1,2,3]
- ATR range: 1.0 - 4.0

## Stats (as of 1405/07/21)
- 13 signals, 8W/5L, WR 61.5%, PF 2.0
- Max DD -11.56

## TODO
- [ ] جمع ۲۰ ترید با v3
- [ ] تحلیل Win Rate جدید
- [ ] شاید R:R v3 خیلی پایین بود → تنظیم کن