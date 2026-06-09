with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # 壊れたtryブロックを検出して修正
    if line.strip() == 'try:' and i + 1 < len(lines):
        next_line = lines[i + 1]
        if next_line.strip().startswith('state = await self.elfa.get_query'):
            indent = '            '
            new_lines.append(indent + 'try:\n')
            new_lines.append(indent + '    state = await self.elfa.get_query(query_id)\n')
            new_lines.append(indent + 'except Exception as _e:\n')
            new_lines.append(indent + '    import logging\n')
            new_lines.append(indent + '    logging.getLogger(__name__).warning(str(_e))\n')
            new_lines.append(indent + '    await asyncio.sleep(15)\n')
            new_lines.append(indent + '    continue\n')
            i += 2  # 元のtry:とstate行をスキップ
            continue
    new_lines.append(line)
    i += 1

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('OK - indent fixed')

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(65, min(len(lines), 82)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
