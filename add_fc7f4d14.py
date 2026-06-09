# fc7f4d14 と新IDをQUERY_ROLESに追加
with open('elfa_grvt_bot/strategy_engine.py', encoding='utf-8') as f:
    content = f.read()

new_ids = {
    'fc7f4d14-fd2c-48a9-9e79-d8436efb8892': 'SHORT_SETUP_15m',
    'df9d80bd-f25d-40af-a743-a75de27e088b': 'SHORT_SETUP_15m',
    '5e93b5bc-3600-468e-b410-cc1ac3ddbf78': 'SHORT_SETUP_15m',
}

added = 0
for qid, role in new_ids.items():
    if qid not in content:
        line = f"    '{qid}': '{role}',\n"
        # QUERY_ROLES の閉じ括弧 } の直前に挿入
        content = content.replace(
            '}\n\nNORMAL_THRESHOLD',
            f"{line}" + '}\n\nNORMAL_THRESHOLD'
        )
        added += 1

if added > 0:
    with open('elfa_grvt_bot/strategy_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'OK - {added} IDs added to QUERY_ROLES')
else:
    print('OK - all IDs already present')

# 確認
with open('elfa_grvt_bot/strategy_engine.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== QUERY_ROLES ===')
for i, l in enumerate(lines):
    if 7 <= i+1 <= 32:
        print(f'{i+1:03}: {l.rstrip()}')
