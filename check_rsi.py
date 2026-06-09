import httpx

def rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * 13 + gains[i]) / 14
        al = (al * 13 + losses[i]) / 14
    return 100 - 100 / (1 + ag / al) if al else 100

def get_closes(interval, limit=50):
    r = httpx.get('https://fapi.binance.com/fapi/v1/klines',
        params={'symbol': 'BTCUSDT', 'interval': interval, 'limit': limit}, timeout=10)
    return [float(k[4]) for k in r.json()]

c15 = get_closes('15m')
c1h = get_closes('1h')
c4h = get_closes('4h')

r15 = rsi(c15)
r1h = rsi(c1h)
r4h = rsi(c4h)

print(f'BTC price : {c1h[-1]:,.1f}')
print(f'RSI 15m   : {r15:.1f}')
print(f'RSI 1h    : {r1h:.1f}')
print(f'RSI 4h    : {r4h:.1f}')
print()
print('--- トリガー予測 ---')
print(f'SHORT_SETUP_15m  (RSI 15m crosses_below 42): {"★今すぐ圏内" if r15 < 42 else f"あと {r15-42:.1f}pt 下落で発火"}')
print(f'BEAR_RSI_CROSS_35(RSI 1h  crosses_below 35): {"★今すぐ圏内" if r1h < 35 else f"あと {r1h-35:.1f}pt 下落で発火"}')
print(f'BEAR_FILTER_V2   (RSI 4h  crosses_below 40): {"★今すぐ圏内" if r4h < 40 else f"あと {r4h-40:.1f}pt 下落で発火"}')
print(f'SHORT_REVERSAL_V2(RSI 4h  crosses_below 45): {"★今すぐ圏内" if r4h < 45 else f"あと {r4h-45:.1f}pt 下落で発火"}')
print(f'BEAR_MOMENTUM_4H (RSI 4h  crosses_below 50): {"★今すぐ圏内" if r4h < 50 else f"あと {r4h-50:.1f}pt 下落で発火"}')
