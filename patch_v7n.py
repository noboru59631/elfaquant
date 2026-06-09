TARGET = 'mm_bot_v7.py'
OLD = 'max_inv         : Decimal = Decimal("0.02")'
NEW = 'max_inv         : Decimal = Decimal("0.10")'
with open(TARGET, encoding='utf-8') as f:
    src = f.read()
if OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(src)
    print('✅ max_inv 0.02 → 0.10 BTC 変更完了')
else:
    print('❌ 対象箇所が見つかりません')
