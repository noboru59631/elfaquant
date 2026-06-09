with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    # 行69 (index 68): state行 → try:を前に挿入
    if i == 68:  # 0-indexed line 69
        new_lines.append('            try:\n')
        new_lines.append('                state = await self.elfa.get_query(query_id)\n')
        i += 1  # 元のstate行をスキップ
        continue
    # 行70 (index 69): except行 → そのまま維持しraise→sleepに変更
    if i == 69:  # except Exception as e:
        new_lines.append('            except Exception as e:\n')
        i += 1
        continue
    # 行76 (index 75): raise → sleep+continueに変更
    if i == 75 and lines[i].strip() == 'raise':
        new_lines.append('                await asyncio.sleep(15)\n')
        new_lines.append('                continue\n')
        i += 1
        continue
    new_lines.append(lines[i])
    i += 1

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('OK - fixed')

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(64, 82):
    print(f'{i+1:03}: {lines[i].rstrip()}')
