"""test_order3.py"""
import asyncio, pathlib, logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

async def main():
    from elfa_grvt_bot.grvt_client import GrvtClient
    grvt = GrvtClient(
        api_key     = env.get('GRVT_TRADING_API_KEY', ''),
        private_key = env.get('GRVT_TRADING_PRIVATE_KEY', '')
    )
    try:
        ok = await grvt.login()
        print(f"Login: {ok}, Account: {grvt.account_id}")
        if not ok:
            return
        price = await grvt.fetch_mid_price('BTC_USDT_Perp')
        print(f"BTC price: {price}")
        print("\n--- Placing SELL 0.001 BTC_USDT_Perp (market) ---")
        result = await grvt.place_entry_with_tpsl(
            symbol='BTC_USDT_Perp',
            entry_side='sell',
            amount=0.001,
            order_type='market',
            reference_price=price,
        )
        print(f"\nResult: {result}")
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        await grvt.close()

asyncio.run(main())
