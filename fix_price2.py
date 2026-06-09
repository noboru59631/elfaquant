with open('elfa_grvt_bot/scorer.py', encoding='utf-8') as f:
    lines = f.readlines()

# snap['price']が設定されている行を全て表示
print('=== snap[price] assignments ===')
for i, line in enumerate(lines):
    if \"snap['price']\" in line:
        print(f'{i+1}: {repr(line.rstrip())}')

# fetch_market_snapshot関数内のprice設定を確認
in_func = False
for i, line in enumerate(lines):
    if 'def fetch_market_snapshot' in line:
        in_func = True
    if in_func and 'k5m' in line and 'price' in line.lower():
        print(f'k5m price line {i+1}: {repr(line.rstrip())}')
    if in_func and i > 0 and line.startswith('def ') and 'fetch_market' not in line:
        in_func = False