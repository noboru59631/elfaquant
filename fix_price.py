with open('elfa_grvt_bot/scorer.py', encoding='utf-8') as f:
    content = f.read()

# lastPriceをpriceとして確実に取得するよう修正
old = "last=float(t.get('lastPrice') or 0); snap['price'] = last if last>0 else snap.get('price', float(k5m[-1][4]))"
new = """last = float(t.get('lastPrice') or 0)
        if last > 0:
            snap['price'] = last
        if not snap.get('price') or snap['price'] == 0:
            snap['price'] = float(k5m[-1][4])"""

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/scorer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - price fix applied')
else:
    # 直接 fetch_market_snapshot の先頭でklineからpriceをセット
    old2 = "    # -- Price --\n    snap['price'] = float(k5m[-1][4])"
    new2 = "    # -- Price (set from kline first as reliable baseline) --\n    snap['price'] = float(k5m[-1][4])"
    if old2 in content:
        content = content.replace(old2, new2)
        with open('elfa_grvt_bot/scorer.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('OK - price baseline set from kline')
    else:
        # klineのprice設定箇所を確認
        for i, line in enumerate(content.splitlines()):
            if "snap['price']" in line:
                print(f'{i+1}: {repr(line)}')