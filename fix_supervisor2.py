with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 35-44 (index 34-43) をコメントアウト
for i in range(34, 44):
    if not lines[i].startswith('            #') and lines[i].strip():
        lines[i] = '            # DISABLED: ' + lines[i].lstrip()

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('OK - auto-reset disabled')

# 確認
print()
print('=== Lines 34-46 after fix ===')
for i in range(33, 46):
    print(f'{i+1:03}: {lines[i].rstrip()}')
