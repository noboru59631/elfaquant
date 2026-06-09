import httpx

# 実際のAPIレスポンスを確認
urls = [
    "https://market-data.grvt.io/full/v1/mini_ticker?instrument=BTC_USDT_Perp",
    "https://market-data.grvt.io/full/v1/mini_ticker?instrument=BTC_USDT_PERP",
    "https://market-data.grvt.io/full/v1/ticker?instrument=BTC_USDT_Perp",
    "https://market-data.grvt.io/full/v1/instruments",
]

for url in urls:
    try:
        r = httpx.get(url, timeout=10)
        print(f'Status: {r.status_code} | URL: {url}')
        if r.status_code == 200:
            import json
            data = r.json()
            print(f'  Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}')
            print(f'  Preview: {str(data)[:300]}')
        else:
            print(f'  Body: {r.text[:200]}')
    except Exception as e:
        print(f'ERROR: {e} | URL: {url}')
    print()
