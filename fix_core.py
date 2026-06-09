with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# 壊れたtryブロックを全パターン除去して元に戻す
import re

# パターン1: try:\n    state = ...
content = re.sub(
    r'[ \t]+try:\n[ \t]+try:\n[ \t]+state = await self\.elfa\.get_query\(query_id\)',
    '            state = await self.elfa.get_query(query_id)',
    content
)

# パターン2: try: が単独で残っている場合
content = re.sub(
    r'[ \t]+try:\n([ \t]+state = await self\.elfa\.get_query\(query_id\))',
    r'            \1',
    content
)

# 壊れたexceptブロックも除去
content = re.sub(
    r'\n[ \t]+except Exception as _e:\n[ \t]+import logging\n[ \t]+logging\.getLogger.*\n[ \t]+await asyncio\.sleep\(15\)\n[ \t]+continue',
    '',
    content
)

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK - core.py cleaned')

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(60, min(len(lines), 80)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
