import asyncio, pathlib
from decimal import Decimal
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

ENTRY = 74577.0
SIZE  = Decimal("0.02")
TP    = round(ENTRY * 0.965, 1)
SL    = round(ENTRY * 1.015, 1)

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()
    print(f"TP: ${TP:,.1f}  SL: ${SL:,.1f}")
    tp = await grvt._place_single_order(
        symbol="BTC_USDT_Perp", is_buying=True, amount=SIZE,
        is_market=False, limit_price=Decimal(str(TP)),
        time_in_force="GTC", reduce_only=True)
    print(f"TP: {tp}")
    sl = await grvt._place_single_order(
        symbol="BTC_USDT_Perp", is_buying=True, amount=SIZE,
        is_market=False, limit_price=Decimal(str(SL)),
        time_in_force="GTC", reduce_only=True)
    print(f"SL: {sl}")
    await grvt.close()

asyncio.run(main())
