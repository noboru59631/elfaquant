"""fix_registry_conn.py - update_fire_outcome の _conn を sqlite3.connect に修正"""
import re

with open('elfa_grvt_bot/registry.py', encoding='utf-8') as f:
    content = f.read()

# _conn.execute / _conn.commit を置換
old_exec   = 'self._conn.execute('
new_exec   = 'conn.execute('
old_commit = 'self._conn.commit()'
new_commit = 'conn.commit()'

# update_fire_outcome メソッド全体をパターンで置換
pattern = re.compile(
    r'(    def update_fire_outcome\(.*?\n)'   # def行
    r'(.*?)'                                   # 引数部分
    r'(        try:\n)'                        # try:
    r'(            self\._conn\.execute\()',   # self._conn.execute(
    re.DOTALL
)

if '_conn' in content:
    content = content.replace('            self._conn.execute(', '            with sqlite3.connect(self.db_path) as conn:\n                conn.execute(')
    content = content.replace('            self._conn.commit()\n            return True', '                pass\n            return True')
    with open('elfa_grvt_bot/registry.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - _conn replaced')
else:
    print('_conn not found - already fixed or different structure')

# 確認
with open('elfa_grvt_bot/registry.py', encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
for i, l in enumerate(lines):
    if 'def update_fire_outcome' in l:
        for j in range(i, min(i+40, len(lines))):
            print(f'{j+1:03}: {lines[j].rstrip()}')
        break
