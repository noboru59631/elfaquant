with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # line 95 (index 94): コメント行はそのまま
    # line 96 (index 95): passのインデントを修正
    if i == 95 and 'pass  # await self.sync_terminal_status' in line:
        new_lines.append('                pass  # sync_terminal_status disabled\n')
    else:
        new_lines.append(line)

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('OK - indent fixed')

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(89, 102):
    print(f'{i+1:03}: {lines[i].rstrip()}')
