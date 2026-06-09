import httpx

# Binance Futures ticker APIのレスポンスを確認
url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
r = httpx.get(url, params={'symbol': 'BTCUSDT'}, timeout=10)
print('Status:', r.status_code)
data = r.json()
print('Keys:', list(data.keys()) if isinstance(data, dict) else 'LIST type')
print('lastPrice:', data.get('lastPrice'))
print('askPrice:', data.get('askPrice'))
print('bidPrice:', data.get('bidPrice'))
print('price:', data.get('price'))

# klineからのprice確認
url2 = 'https://fapi.binance.com/fapi/v1/klines'
r2 = httpx.get(url2, params={'symbol': 'BTCUSDT', 'interval': '5m', 'limit': 3}, timeout=10)
klines = r2.json()
print('\nLatest 5m close:', float(klines[-1][4]))
print('Latest 5m high:', float(klines[-1][2]))