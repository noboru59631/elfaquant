import asyncio, pathlib

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

api_key = env.get('GRVT_TRADING_API_KEY', '')
private_key = env.get('GRVT_TRADING_PRIVATE_KEY', '')

print(f'API_KEY: {api_key[:8]}...{api_key[-4:] if len(api_key)>8 else "(short)"}')
print(f'PRIVATE_KEY: {"SET" if private_key else "MISSING"}')

async def test():
    from elfa_grvt_bot.grvt_client import GrvtClient
    grvt = GrvtClient(api_key, private_key)
    try:
        result = await grvt.login()
        print(f'Login result: {result}')
        print(f'Cookie: {"SET" if grvt.cookie else "MISSING"}')
        print(f'Account ID: {grvt.account_id}')
    except Exception as e:
        print(f'Login ERROR: {e}')
    finally:
        await grvt.client.aclose()

asyncio.run(test())
