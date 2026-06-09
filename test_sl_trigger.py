import asyncio, pathlib
from decimal import Decimal
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

ENTRY = 74578.0
SIZE  = Decimal("0.02")
SL    = round(ENTRY * 1.015, 1)  # +1.5% = 75,697.0

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()
    print(f"SL trigger price: ${SL:,.1f}")
    result = await grvt.place_entry_with_tpsl(
        symbol="BTC_USDT_Perp",
        entry_side="sell",
        amount=0.0,
        order_type="market",
        reference_price=ENTRY,
        sl_price=SL,
    )
    print(f"Result: {result}")
    await grvt.close()

asyncio.run(main())
