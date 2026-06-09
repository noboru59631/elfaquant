# patch_v7h.py — SIZE/MAX_POS変数名修正パッチ
with open('mm_bot_v7.py', encoding='utf-8') as f:
    content = f.read()

changes = [
    # base_size: 0.02 → 0.01
    ('base_size       : Decimal = Decimal("0.02")',
     'base_size       : Decimal = Decimal("0.01")'),
    # max_inv: 0.04 → 0.02
    ('max_inv         : Decimal = Decimal("0.04")',
     'max_inv         : Decimal = Decimal("0.02")'),
]

applied = 0
for old, new in changes:
    if old in content:
        content = content.replace(old, new)
        print(f'✅ {old.split(":")[0].strip()} 修正完了')
        applied += 1
    else:
        print(f'❌ 見つからない: {old[:50]}')

if applied > 0:
    with open('mm_bot_v7.py', 'w', encoding='utf-8') as f:
        f.write(content)

print(f'\n適用済み: {applied}/2')

# 確認表示
print('\n=== 修正後の設定値確認 ===')
for line in content.splitlines():
    if any(k in line for k in ['base_size', 'max_inv', 'daily_loss_limit', 'run_forever', 'CUMULATIVE_LIMIT', 'COOLDOWN_MIN']):
        print(f'  {line.strip()}')
