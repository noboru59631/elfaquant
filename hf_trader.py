import asyncio, pathlib, time
from decimal import Decimal
import httpx
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

# ===== 高頻度戦略設定 =====
SYMBOL         = "BTC_USDT_Perp"
SIZE           = Decimal("0.02")
TP_PCT         = 0.015   # -1.5% 利確
SL_PCT         = 0.005   # +0.5% 損切
CHECK_INTERVAL = 3
MAX_TRADES     = 100
# ==========================

async def get_price(client: httpx.AsyncClient) -> float:
    r = await client.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": "BTCUSDT"}
    )
    return float(r.json()["price"])

async def place_order(grvt: GrvtClient, is_buying: bool, reduce_only: bool, reason: str):
    result = await grvt._place_single_order(
        symbol        = SYMBOL,
        is_buying     = is_buying,
        amount        = SIZE,
        is_market     = True,
        limit_price   = None,
        time_in_force = "IOC",
        reduce_only   = reduce_only,
    )
    print(f"  [{reason}] {'BUY' if is_buying else 'SELL'} → {result.get('status','?')}")
    return result

async def run_one_trade(grvt: GrvtClient, client: httpx.AsyncClient, trade_num: int):
    entry_price = await get_price(client)
    tp_price = entry_price * (1 - TP_PCT)
    sl_price = entry_price * (1 + SL_PCT)

    print(f"\n{'='*45}")
    print(f"  トレード #{trade_num}  [{time.strftime('%H:%M:%S')}]")
    print(f"  エントリー: ${entry_price:,.1f}")
    print(f"  TP: ${tp_price:,.1f} (-1.5%)  SL: ${sl_price:,.1f} (+0.5%)")
    print(f"{'='*45}")

    await place_order(grvt, is_buying=False, reduce_only=False, reason="ショートエントリー")
    await asyncio.sleep(1)

    while True:
        try:
            price = await get_price(client)
            pnl_pct = (entry_price - price) / entry_price * 100
            print(f"  [{time.strftime('%H:%M:%S')}] ${price:,.1f}  損益: {pnl_pct:+.2f}%", end="\r")

            if price <= tp_price:
                print(f"\n  ✅ TP利確 ${price:,.1f}  (+{TP_PCT*100:.1f}%)")
                await place_order(grvt, is_buying=True, reduce_only=True, reason="TP利確")
                return "TP", entry_price, price

            if price >= sl_price:
                print(f"\n  ❌ SL損切 ${price:,.1f}  (-{SL_PCT*100:.1f}%)")
                await place_order(grvt, is_buying=True, reduce_only=True, reason="SL損切")
                return "SL", entry_price, price

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"\n  エラー: {e}")
            await asyncio.sleep(5)
            try:
                await grvt.login()
            except:
                pass

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()

    print("=" * 45)
    print("  高頻度ショート自動売買 開始")
    print(f"  TP: -1.5%  SL: +0.5%  最大{MAX_TRADES}回")
    print(f"  損益分岐勝率: 28.7%")
    print("=" * 45)

    tp_count  = 0
    sl_count  = 0
    total_pnl = 0.0
    FEE_RATE  = 0.00037  # 往復手数料

    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(1, MAX_TRADES + 1):
            result, entry, exit_price = await run_one_trade(grvt, client, i)

            # 損益計算
            trade_pnl = (entry - exit_price) / entry * float(SIZE) * exit_price
            fee       = float(SIZE) * exit_price * FEE_RATE
            net_pnl   = trade_pnl - fee
            total_pnl += net_pnl

            if result == "TP":
                tp_count += 1
            else:
                sl_count += 1

            volume = i * float(SIZE) * entry * 2  # 往復

            print(f"  純損益: {net_pnl:+.2f} USDT  累計: {total_pnl:+.2f} USDT")
            print(f"  TP {tp_count}勝 / SL {sl_count}敗  勝率: {tp_count/i*100:.1f}%")
            print(f"  累計取引量: ${volume:,.0f} USDT")

            await asyncio.sleep(2)

    await grvt.close()
    print("\n自動売買終了")
    print(f"最終損益: {total_pnl:+.2f} USDT")

asyncio.run(main())
