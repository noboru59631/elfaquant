import asyncio, pathlib
from decimal import Decimal
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

SYMBOL        = "BTC_USDT_Perp"
ENTRY_PRICE   = 75060.0
POSITION_SIZE = Decimal("0.02")
SL_PRICE      = round(75060.0 * 1.015, 1)   # +1.5% = 76185.9
TP_PRICE      = round(75060.0 * 0.965, 1)   # -3.5% = 72432.9

print(f"SL: ${SL_PRICE:,.1f}  TP: ${TP_PRICE:,.1f}")

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    try:
        await grvt.login()
        print(f"Login OK: {grvt.account_id}")
        sl = await grvt._place_single_order(
            symbol=SYMBOL, is_buying=True, amount=POSITION_SIZE,
            is_market=False, limit_price=Decimal(str(SL_PRICE)),
            time_in_force="GTC", reduce_only=True)
        print(f"SL: {sl}")
        tp = await grvt._place_single_order(
            symbol=SYMBOL, is_buying=True, amount=POSITION_SIZE,
            is_market=False, limit_price=Decimal(str(TP_PRICE)),
            time_in_force="GTC", reduce_only=True)
        print(f"TP: {tp}")
    except Exception as e:
        import traceback; traceback.print_exc()
    finally:
        await grvt.close()

asyncio.run(main())
