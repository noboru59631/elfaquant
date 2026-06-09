import asyncio, pathlib, time, datetime
from decimal import Decimal
import httpx
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

# ===== 設定 =====
SYMBOL            = "BTC_USDT_Perp"
CHECK_INTERVAL    = 3

SIZE_DEFENSE      = Decimal("0.03")
SIZE_NORMAL       = Decimal("0.05")

TP_PCT_DEFENSE    = 0.010
TP_PCT_NORMAL     = 0.015
SL_PCT_DEFENSE    = 0.0035
SL_PCT_NORMAL     = 0.0040

# RSIトレンド判定
RSI_SHORT_ENTRY   = 35    # RSI 1h < 35 → ショート
RSI_LONG_ENTRY    = 65    # RSI 1h > 65 → ロング
RSI_NEUTRAL_LOW   = 35    # レンジ下限
RSI_NEUTRAL_HIGH  = 65    # レンジ上限

# 安全ルール
STOP_BALANCE      = 900.0
MAX_DAILY_LOSS    = 36.0
DEFENSE_LOSS      = 24.0
MAX_CONSEC_SL     = 2
COOLDOWN_MIN      = 30
FEE_RATE          = 0.00090
MAX_TRADES        = 200
# =================

async def get_price(client: httpx.AsyncClient) -> float:
    r = await client.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": "BTCUSDT"}
    )
    return float(r.json()["price"])

async def get_rsi(client: httpx.AsyncClient) -> dict:
    """Binanceから1h RSIを取得"""
    r = await client.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "1h", "limit": 50}
    )
    closes = [float(k[4]) for k in r.json()]
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    period = 14
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        rsi_1h = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_1h = 100 - (100 / (1 + rs))

    # 4h RSI
    r2 = await client.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "4h", "limit": 50}
    )
    closes4 = [float(k[4]) for k in r2.json()]
    gains4, losses4 = [], []
    for i in range(1, len(closes4)):
        diff = closes4[i] - closes4[i-1]
        gains4.append(max(diff, 0))
        losses4.append(max(-diff, 0))
    avg_gain4 = sum(gains4[-period:]) / period
    avg_loss4 = sum(losses4[-period:]) / period
    if avg_loss4 == 0:
        rsi_4h = 100.0
    else:
        rs4 = avg_gain4 / avg_loss4
        rsi_4h = 100 - (100 / (1 + rs4))

    return {"1h": round(rsi_1h, 1), "4h": round(rsi_4h, 1)}

def determine_direction(rsi_1h: float, rsi_4h: float) -> str:
    """トレンド方向を判定"""
    # ショート条件: RSI1h < 35 かつ RSI4h < 50
    if rsi_1h < RSI_SHORT_ENTRY and rsi_4h < 50:
        return "SHORT"
    # ロング条件: RSI1h > 65 かつ RSI4h > 50
    if rsi_1h > RSI_LONG_ENTRY and rsi_4h > 50:
        return "LONG"
    # レンジ: 待機
    return "WAIT"

async def get_balance(grvt: GrvtClient) -> float:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://trades.grvt.io/full/v1/account_summary",
            json={"sub_account_id": "7643292000705847"},
            cookies={"gravity": grvt.cookie}
        )
        data = r.json().get("result", {})
        return float(data.get("total_equity", 0))

async def place_order(grvt: GrvtClient, is_buying: bool,
                      size: Decimal, reduce_only: bool, reason: str):
    result = await grvt._place_single_order(
        symbol        = SYMBOL,
        is_buying     = is_buying,
        amount        = size,
        is_market     = True,
        limit_price   = None,
        time_in_force = "IOC",
        reduce_only   = reduce_only,
    )
    side   = "BUY" if is_buying else "SELL"
    status = result.get("status", "?")
    print(f"  [{reason}] {side} {size} BTC → {status}")
    return result

class TradingBot:
    def __init__(self):
        self.mode         = "NORMAL"
        self.consec_sl    = 0
        self.daily_loss   = 0.0
        self.total_pnl    = 0.0
        self.total_volume = 0.0
        self.tp_count     = 0
        self.sl_count     = 0
        self.day_start    = datetime.date.today()

    def reset_daily(self):
        if datetime.date.today() > self.day_start:
            print(f"\n[日次リセット] 前日損益: {self.daily_loss:+.2f} USDT")
            self.daily_loss = 0.0
            self.day_start  = datetime.date.today()
            self.mode       = "NORMAL"

    def get_params(self):
        if self.mode == "DEFENSE":
            return SIZE_DEFENSE, TP_PCT_DEFENSE, SL_PCT_DEFENSE
        return SIZE_NORMAL, TP_PCT_NORMAL, SL_PCT_NORMAL

    def check_safety(self, balance: float) -> str:
        if balance <= STOP_BALANCE:
            return "STOP"
        if self.daily_loss <= -MAX_DAILY_LOSS:
            return "STOP"
        if self.daily_loss <= -DEFENSE_LOSS:
            return "DEFENSE"
        return "OK"

async def run_one_trade(grvt: GrvtClient, client: httpx.AsyncClient,
                        bot: TradingBot, trade_num: int, direction: str):
    bot.reset_daily()
    size, tp_pct, sl_pct = bot.get_params()

    entry_price = await get_price(client)
    notional    = float(size) * entry_price

    is_short = (direction == "SHORT")

    if is_short:
        tp_price = entry_price * (1 - tp_pct)
        sl_price = entry_price * (1 + sl_pct)
        dir_label = "📉 ショート"
    else:
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        dir_label = "📈 ロング"

    print(f"\n{'='*50}")
    print(f"  トレード #{trade_num}  {dir_label}  モード:{bot.mode}")
    print(f"  [{time.strftime('%H:%M:%S')}]  サイズ: {size} BTC")
    print(f"  エントリー: ${entry_price:,.1f}")
    print(f"  TP: ${tp_price:,.1f} "
          f"({'−' if is_short else '+'}{tp_pct*100:.1f}%)")
    print(f"  SL: ${sl_price:,.1f} "
          f"({'＋' if is_short else '−'}{sl_pct*100:.1f}%)")
    print(f"  日次損益: {bot.daily_loss:+.2f}  累計: {bot.total_pnl:+.2f}")
    print(f"{'='*50}")

    # エントリー
    await place_order(grvt, is_buying=not is_short,
                      size=size, reduce_only=False, reason="エントリー")
    await asyncio.sleep(1)

    # TP/SL監視
    while True:
        try:
            price   = await get_price(client)
            if is_short:
                pnl_pct = (entry_price - price) / entry_price * 100
                tp_hit  = price <= tp_price
                sl_hit  = price >= sl_price
            else:
                pnl_pct = (price - entry_price) / entry_price * 100
                tp_hit  = price >= tp_price
                sl_hit  = price <= sl_price

            print(f"  [{time.strftime('%H:%M:%S')}] "
                  f"${price:,.1f}  損益: {pnl_pct:+.3f}%", end="\r")

            if tp_hit:
                print(f"\n  ✅ TP利確 ${price:,.1f}")
                await place_order(grvt, is_buying=is_short,
                                  size=size, reduce_only=True, reason="TP利確")
                fee = notional * FEE_RATE
                if is_short:
                    pnl = (entry_price - price) * float(size) - fee
                else:
                    pnl = (price - entry_price) * float(size) - fee
                return "TP", pnl, notional * 2

            if sl_hit:
                print(f"\n  ❌ SL損切 ${price:,.1f}")
                await place_order(grvt, is_buying=is_short,
                                  size=size, reduce_only=True, reason="SL損切")
                fee = notional * FEE_RATE
                if is_short:
                    pnl = (entry_price - price) * float(size) - fee
                else:
                    pnl = (price - entry_price) * float(size) - fee
                return "SL", pnl, notional * 2

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"\n  エラー: {e}")
            await asyncio.sleep(5)
            try:
                await grvt.login()
            except:
                pass

async def main():
    grvt = GrvtClient(
        env.get("GRVT_TRADING_API_KEY",""),
        env.get("GRVT_TRADING_PRIVATE_KEY","")
    )
    await grvt.login()
    bot = TradingBot()

    print("=" * 50)
    print("  GRVT x ELFA 大会ボット v2（双方向）")
    print("  ショート: RSI1h<35 かつ RSI4h<50")
    print("  ロング  : RSI1h>65 かつ RSI4h>50")
    print("  待機    : RSI1h 35〜65")
    print(f"  通常: {SIZE_NORMAL} BTC  TP:1.5%  SL:0.40%")
    print(f"  防衛: {SIZE_DEFENSE} BTC  TP:1.0%  SL:0.35%")
    print(f"  停止: 残高<$900 / 日次損失>${MAX_DAILY_LOSS}")
    print("=" * 50)

    async with httpx.AsyncClient(timeout=10) as client:
        wait_count = 0
        for i in range(1, MAX_TRADES + 1):

            # 残高チェック
            balance = await get_balance(grvt)
            safety  = bot.check_safety(balance)

            if safety == "STOP":
                print(f"\n🛑 安全停止: 残高${balance:.2f} "
                      f"/ 日次損失${bot.daily_loss:.2f}")
                break

            if safety == "DEFENSE" and bot.mode != "DEFENSE":
                print(f"\n⚠️  防衛モード移行 (日次損失: {bot.daily_loss:+.2f})")
                bot.mode = "DEFENSE"

            # クールダウン
            if bot.consec_sl >= MAX_CONSEC_SL:
                print(f"\n⏸️  連続SL{MAX_CONSEC_SL}回 → {COOLDOWN_MIN}分待機")
                await asyncio.sleep(COOLDOWN_MIN * 60)
                bot.consec_sl = 0
                print("▶️  クールダウン終了")

            # RSI取得・方向判定
            rsi = await get_rsi(client)
            direction = determine_direction(rsi["1h"], rsi["4h"])

            print(f"\n  RSI 1h:{rsi['1h']}  4h:{rsi['4h']}"
                  f"  → {direction}")

            if direction == "WAIT":
                wait_count += 1
                print(f"  ⏳ 待機中... ({wait_count}回目)  "
                      f"次のチェックまで60秒")
                await asyncio.sleep(60)
                i -= 1  # カウントしない
                continue

            wait_count = 0

            # トレード実行
            result, pnl, volume = await run_one_trade(
                grvt, client, bot, i, direction)

            bot.daily_loss   += pnl
            bot.total_pnl    += pnl
            bot.total_volume += volume

            if result == "TP":
                bot.tp_count  += 1
                bot.consec_sl  = 0
            else:
                bot.sl_count  += 1
                bot.consec_sl += 1

            total = bot.tp_count + bot.sl_count
            print(f"  純損益: {pnl:+.2f} USDT  "
                  f"累計: {bot.total_pnl:+.2f} USDT")
            print(f"  TP {bot.tp_count}勝 / SL {bot.sl_count}敗  "
                  f"勝率: {bot.tp_count/total*100:.1f}%")
            print(f"  累計取引量: ${bot.total_volume:,.0f}  "
                  f"残高: ${balance:.2f}")

            await asyncio.sleep(2)

    await grvt.close()
    print(f"\n{'='*50}")
    print(f"  自動売買終了")
    print(f"  最終損益:   {bot.total_pnl:+.2f} USDT")
    print(f"  累計取引量: ${bot.total_volume:,.0f} USDT")
    print(f"  勝敗: TP {bot.tp_count}勝 / SL {bot.sl_count}敗")
    print(f"{'='*50}")

asyncio.run(main())
