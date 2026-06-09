import asyncio, pathlib
from decimal import Decimal
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()
    result = await grvt._place_single_order(
        symbol="BTC_USDT_Perp", is_buying=True,
        amount=Decimal("0.02"), is_market=True,
        limit_price=None, time_in_force="IOC", reduce_only=True)
    print("クローズ結果:", result)
    await grvt.close()

asyncio.run(main())
