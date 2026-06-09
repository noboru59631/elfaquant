with open('elfa_grvt_bot/scorer.py', encoding='utf-8') as f:
    content = f.read()

# ticker取得失敗時のfallbackを強化
old = '''    # -- Spread (bid/ask from ticker) --
    try:
        t = _ticker_24h(symbol)
        snap['spread'] = float(t.get('askPrice', 0)) - float(t.get('bidPrice', 0))
        snap['price']  = float(t.get('lastPrice', snap.get('price', 0)))
    except Exception as e:
        snap['errors'].append(f'ticker: {e}')
        snap['spread'] = 5.0'''

new = '''    # -- Spread (bid/ask from ticker) --
    try:
        t = _ticker_24h(symbol)
        ask = float(t.get('askPrice') or 0)
        bid = float(t.get('bidPrice') or 0)
        last = float(t.get('lastPrice') or t.get('price') or 0)
        if ask > 0 and bid > 0:
            snap['spread'] = ask - bid
        else:
            snap['spread'] = snap.get('price', 77000) * 0.00005
        if last > 0:
            snap['price'] = last
        if not snap.get('price'):
            snap['price'] = float(k5m[-1][4])
    except Exception as e:
        snap['errors'].append(f'ticker: {e}')
        snap['spread'] = snap.get('price', 77000) * 0.00005
        if not snap.get('price'):
            snap['price'] = float(k5m[-1][4])'''

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/scorer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - ticker fallback fixed')
else:
    # 別パターンで修正
    content = content.replace(
        "snap['spread'] = float(t.get('askPrice', 0)) - float(t.get('bidPrice', 0))",
        "ask=float(t.get('askPrice') or 0); bid=float(t.get('bidPrice') or 0); snap['spread'] = (ask-bid) if ask>0 and bid>0 else snap.get('price',77000)*0.00005"
    )
    content = content.replace(
        "snap['price']  = float(t.get('lastPrice', snap.get('price', 0)))",
        "last=float(t.get('lastPrice') or 0); snap['price'] = last if last>0 else snap.get('price', float(k5m[-1][4]))"
    )
    with open('elfa_grvt_bot/scorer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - ticker fallback fixed (alt pattern)')