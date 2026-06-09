import asyncio, pathlib
from elfa_grvt_bot.grvt_client import GrvtClient

async def close():
    env = {k.strip(): v.strip()
           for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines()
           if '=' in line and not line.startswith('#')
           for k, v in [line.split('=', 1)]}
    grvt = GrvtClient(
        api_key=env['GRVT_TRADING_API_KEY'],
        private_key=env['GRVT_TRADING_PRIVATE_KEY'])
    await grvt.login()
    from mm_bot_v6 import get_account_data, cancel_all as ca
    await ca(grvt)
    print('全注文キャンセル完了')
    acct = await get_account_data(grvt)
    for p in acct.get('positions', []):
        if p.get('instrument') == 'BTC_USDT_Perp':
            size = float(p['size'])
            print('残ポジション: ' + str(size) + ' BTC')
            if size > 0:
                await grvt._place_single_order(
                    symbol='BTC_USDT_Perp', is_buying=False,
                    amount=abs(size), is_market=True,
                    limit_price=None,
                    time_in_force='IOC',
                    post_only=False, reduce_only=True)
                print('成行クローズ注文送信完了')
    await grvt.close()

asyncio.run(close())
