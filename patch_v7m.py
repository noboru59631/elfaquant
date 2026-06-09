TARGET = 'mm_bot_v7.py'
OLD = 'base_size       : Decimal = Decimal("0.02")'
NEW = 'base_size       : Decimal = Decimal("0.05")'
with open(TARGET, encoding='utf-8') as f:
    src = f.read()
if OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(src)
    print('✅ base_size 0.02 → 0.05 BTC 変更完了')
else:
    print('❌ 対象箇所が見つかりません')
