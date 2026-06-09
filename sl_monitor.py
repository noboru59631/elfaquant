import asyncio, pathlib, time
from decimal import Decimal
import httpx
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

# ===== 設定 =====
SYMBOL      = "BTC_USDT_Perp"
POSITION_SIZE = Decimal("0.02")
ENTRY_PRICE   = 74497.5
SL_PRICE      = round(ENTRY_PRICE * 1.015, 1)   # +1.5% = 75,615.0
TP_PRICE      = round(ENTRY_PRICE * 0.965, 1)   # -3.5% = 71,890.1
CHECK_INTERVAL = 5   # 秒ごとに価格チェック
# ================

async def get_mark_price(client: httpx.AsyncClient) -> float:
    r = await client.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": "BTCUSDT"}
    )
    return float(r.json()["price"])

async def close_position(grvt: GrvtClient, reason: str):
    print(f"\n[{reason}] クローズ注文送信中...")
    result = await grvt._place_single_order(
        symbol        = SYMBOL,
        is_buying     = True,
        amount        = POSITION_SIZE,
        is_market     = True,
        limit_price   = None,
        time_in_force = "IOC",
        reduce_only   = True,
    )
    print(f"[{reason}] 結果: {result}")
    return result

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()
    print(f"Login OK")
    print(f"監視開始: SELL 0.02 BTC @ ${ENTRY_PRICE:,.1f}")
    print(f"TP: ${TP_PRICE:,.1f}  SL: ${SL_PRICE:,.1f}")
    print(f"チェック間隔: {CHECK_INTERVAL}秒\n")

    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                price = await get_mark_price(client)
                pnl_pct = (ENTRY_PRICE - price) / ENTRY_PRICE * 100
                print(f"[{time.strftime('%H:%M:%S')}] 価格: ${price:,.1f}  損益: {pnl_pct:+.2f}%", end="\r")

                # SL判定（価格が上昇 → ショートの損切）
                if price >= SL_PRICE:
                    await close_position(grvt, "SL損切")
                    break

                # TP判定（価格が下落 → ショートの利確）
                if price <= TP_PRICE:
                    await close_position(grvt, "TP利確")
                    break

                await asyncio.sleep(CHECK_INTERVAL)

            except Exception as e:
                print(f"\nエラー: {e}")
                await asyncio.sleep(10)
                # ログイン切れ対応
                try:
                    await grvt.login()
                except:
                    pass

    await grvt.close()
    print("\n監視終了")

asyncio.run(main())
