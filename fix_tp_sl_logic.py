with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

old = """        if entry_side == 'buy':
            if kind == 'tp': return float(reference) * (1 - pct_frac)
            if kind == 'sl': return float(reference) * (1 - pct_frac)
        if entry_side == 'sell':
            if kind == 'tp': return float(reference) * (1 - pct_frac)
            if kind == 'sl': return float(reference) * (1 + pct_frac)"""

new = """        if entry_side == 'buy':
            if kind == 'tp': return float(reference) * (1 + pct_frac)
            if kind == 'sl': return float(reference) * (1 - pct_frac)
        if entry_side == 'sell':
            if kind == 'tp': return float(reference) * (1 - pct_frac)
            if kind == 'sl': return float(reference) * (1 + pct_frac)"""

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - TP/SL logic fixed')
else:
    print('ERROR: pattern not found')

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== Lines 377-386 after fix ===')
for i in range(376, 386):
    print(f'{i+1:03}: {lines[i].rstrip()}')
