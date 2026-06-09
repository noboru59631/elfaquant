with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

# line 94 (index 93) 周辺を確認して修正
print('Lines 90-100:')
for i in range(89, min(len(lines), 101)):
    print(f'{i+1:03}: {repr(lines[i])}')
