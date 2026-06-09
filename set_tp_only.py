import asyncio, pathlib
from decimal import Decimal
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

ENTRY = 74497.5
SIZE  = Decimal("0.02")
TP    = round(ENTRY * 0.965, 1)  # -3.5% = 71,890.1

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()
    print(f"TP: ${TP:,.1f}")
    tp = await grvt._place_single_order(
        symbol="BTC_USDT_Perp", is_buying=True, amount=SIZE,
        is_market=False, limit_price=Decimal(str(TP)),
        time_in_force="GTC", reduce_only=True)
    print("TP結果:", tp)
    await grvt.close()

asyncio.run(main())
