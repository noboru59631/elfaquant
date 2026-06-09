import asyncio, pathlib, json

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

async def test():
    from elfa_grvt_bot.grvt_client import GrvtClient
    import httpx

    grvt = GrvtClient(
        env.get('GRVT_TRADING_API_KEY', ''),
        env.get('GRVT_TRADING_PRIVATE_KEY', '')
    )
    try:
        ok = await grvt.login()
        print(f'Login: {ok}, Account: {grvt.account_id}')

        # Get price
        r = await grvt.client.post(
            'https://market-data.grvt.io/full/v1/mini',
            json={'instrument': 'BTC_USDT_Perp'}, timeout=10)
        price = r.json().get('result', {}).get('mark_price', '75000')
        print(f'BTC price: {price}')

        # Build order manually to see the payload
        from decimal import Decimal
        parent_order = await grvt._build_order(
            symbol='BTC_USDT_Perp',
            side='sell',
            amount=Decimal('0.001'),
            order_type='market',
            limit_price=None,
            time_in_force='GTC',
            reduce_only=False
        )
        print(f'\n=== Order payload ===')
        print(json.dumps(parent_order, indent=2, default=str))

        # Send raw request to see full error
        body = {
            'sub_account_id': grvt.account_id,
            'orders': [parent_order],
            'order_i_ds': [],
            'client_order_i_ds': [],
            'time_to_live_ms': '500'
        }
        print(f'\n=== Full request body ===')
        print(json.dumps(body, indent=2, default=str))

        response = await grvt.client.post(
            'https://trades.grvt.io/full/v2/bulk_orders',
            json=body,
            headers={
                'Cookie': f'gravity={grvt.cookie}',
                'X-Grvt-Account-Id': grvt.account_id
            },
            timeout=10
        )
        print(f'\nStatus: {response.status_code}')
        print(f'Response: {response.text[:500]}')

    except Exception as e:
        print(f'ERROR: {e}')
    finally:
        await grvt.client.aclose()

asyncio.run(test())
