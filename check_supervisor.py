with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

print('=== Lines 30-55 (Supervisor周辺) ===')
for i in range(29, min(len(lines), 56)):
    print(f'{i+1:03}: {repr(lines[i])}')
