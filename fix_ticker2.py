with open('elfa_grvt_bot/scorer.py', encoding='utf-8') as f:
    content = f.read()

# _ticker_24h関数を完全置換 - bookTickerでask/bidを取得
old_func = '''def _ticker_24h(symbol: str) -> dict:
    url = f'{BINANCE_BASE}/fapi/v1/ticker/24hr'
    r = httpx.get(url, params={'symbol': symbol}, timeout=10)
    r.raise_for_status()
    return r.json()'''

new_func = '''def _ticker_24h(symbol: str) -> dict:
    # 24h ticker (lastPrice, volume etc.)
    url = f'{BINANCE_BASE}/fapi/v1/ticker/24hr'
    r = httpx.get(url, params={'symbol': symbol}, timeout=10)
    r.raise_for_status()
    data = r.json()
    # bookTicker (ask/bid spread)
    try:
        url2 = f'{BINANCE_BASE}/fapi/v1/ticker/bookTicker'
        r2 = httpx.get(url2, params={'symbol': symbol}, timeout=10)
        book = r2.json()
        data['askPrice'] = book.get('askPrice')
        data['bidPrice']  = book.get('bidPrice')
    except Exception:
        pass
    return data'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open('elfa_grvt_bot/scorer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - _ticker_24h replaced with bookTicker support')
else:
    print('Pattern not found - showing _ticker_24h context:')
    for i, line in enumerate(content.splitlines()):
        if 'ticker' in line.lower() and 'def' in line:
            print(f'  {i+1}: {repr(line)}')