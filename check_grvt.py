# 1. Registry のメソッド確認
print('=== Registry methods ===')
with open('elfa_grvt_bot/registry.py', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'def ' in line:
            print(f'{i+1:03}: {line.rstrip()}')

# 2. grvt_client.py の fetch_mid_price 確認
print()
print('=== grvt_client.py fetch_mid_price ===')
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'fetch_mid' in line or 'market-data' in line or 'ticker' in line or 'instruments' in line:
        print(f'{i+1:03}: {line.rstrip()}')

# 3. finalize_failure 確認
print()
print('=== core.py finalize_failure ===')
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(len(lines)):
    if 'finalize_failure' in lines[i] or 'update_fire_outcome' in lines[i]:
        print(f'{i+1:03}: {lines[i].rstrip()}')
