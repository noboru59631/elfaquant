TARGET = 'mm_bot_v7.py'
OLD = 'base_size       : Decimal = Decimal("0.015")'
NEW = 'base_size       : Decimal = Decimal("0.02")'
with open(TARGET, encoding='utf-8') as f:
    src = f.read()
if OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(src)
    print('✅ base_size 0.015 → 0.02 BTC 変更完了')
else:
    print('❌ 対象箇所が見つかりません')
