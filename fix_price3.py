with open('elfa_grvt_bot/scorer.py', encoding='utf-8') as f:
    content = f.read()

# k5mロード後に必ずpriceをセットする行を挿入
old = "    # -- Price (set from kline first as reliable baseline) --\n    snap['price'] = float(k5m[-1][4])"
new = "    # -- Price (always set from kline as baseline) --\n    snap['price'] = float(k5m[-1][4])\n    _price_from_kline = float(k5m[-1][4])"

if old in content:
    content = content.replace(old, new)
    # tickerのprice上書きも確実に動くよう修正
    content = content.replace(
        "        if last > 0:\n            snap['price'] = last\n        if not snap.get('price') or snap['price'] == 0:\n            snap['price'] = float(k5m[-1][4])",
        "        if last > 0:\n            snap['price'] = last"
    )
    with open('elfa_grvt_bot/scorer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    # 別アプローチ: fetch_market_snapshot の return直前にprice保証を追加
    old3 = "    return snap\n"
    new3 = "    # Final price guarantee\n    if not snap.get('price') or snap['price'] == 0:\n        snap['price'] = float(k5m[-1][4])\n    return snap\n"
    # 最後のreturn snapだけ置換
    idx = content.rfind("    return snap\n")
    if idx >= 0:
        content = content[:idx] + new3 + content[idx+len("    return snap\n"):]
        with open('elfa_grvt_bot/scorer.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('OK - price guarantee added before return')
    else:
        print('ERROR - could not find return snap')