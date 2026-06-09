import asyncio, pathlib

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

async def test():
    from elfa_grvt_bot.grvt_client import GrvtClient
    grvt = GrvtClient(
        env.get('GRVT_TRADING_API_KEY', ''),
        env.get('GRVT_TRADING_PRIVATE_KEY', '')
    )
    try:
        # Login
        ok = await grvt.login()
        print(f'Login: {ok}, Account: {grvt.account_id}')

        # Get price
        import httpx
        r = await grvt.client.post(
            'https://market-data.grvt.io/full/v1/mini',
            json={'instrument': 'BTC_USDT_Perp'}, timeout=10)
        price = r.json().get('result', {}).get('mark_price', '75000')
        print(f'BTC price: {price}')

        # Place test order (最小ロット 0.001 BTC)
        result = await grvt.place_entry_with_tpsl(
            symbol='BTC_USDT_Perp',
            entry_side='sell',
            amount=0.001,
            order_type='market',
            limit_price=None,
            time_in_force='GTC',
            reference_price=float(price),
            tp_price=None,
            sl_price=None
        )
        print(f'Order result: {result}')

    except Exception as e:
        print(f'ERROR: {e}')
    finally:
        await grvt.client.aclose()

asyncio.run(test())
