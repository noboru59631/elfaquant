with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # fire_exists の呼び出しを含む行を修正
    if 'fire_exists' in line:
        indent = '                '
        new_lines.append(indent + '# fire_exists replaced with always-process\n')
        new_lines.append(indent + 'if True:\n')
        print(f'Fixed line {i+1}: {line.rstrip()}')
    else:
        new_lines.append(line)

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('OK - fire_exists fixed')

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(319, min(len(lines), 335)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
