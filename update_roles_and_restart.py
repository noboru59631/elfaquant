# Step1: 新IDをQUERY_ROLESに追加
with open('elfa_grvt_bot/strategy_engine.py', encoding='utf-8') as f:
    content = f.read()

additions = """    'df9d80bd-f25d-40af-a743-a75de27e088b': 'SHORT_SETUP_15m',     # SHORT_NOW_1H
    '5e93b5bc-3600-468e-b410-cc1ac3ddbf78': 'SHORT_SETUP_15m',     # SHORT_NOW_4H
"""

# 既存のQUERY_ROLES末尾 "}" の前に挿入
if 'df9d80bd' not in content:
    old = "    '9f71f044-0d33-4409-bbaa-2be1545bddb0': 'SHORT_SETUP_15m',     # 追加クエリ\n}"
    new = "    '9f71f044-0d33-4409-bbaa-2be1545bddb0': 'SHORT_SETUP_15m',     # 追加クエリ\n" + additions + "}"
    if old in content:
        content = content.replace(old, new)
        with open('elfa_grvt_bot/strategy_engine.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('OK - new IDs added to QUERY_ROLES')
    else:
        print('WARN - pattern not found, appending manually')
        # 別アプローチ: } を含む行を探して挿入
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == '}' and i > 5 and i < 25:
                lines.insert(i, additions.rstrip())
                break
        with open('elfa_grvt_bot/strategy_engine.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print('OK - new IDs added (line method)')
else:
    print('OK - IDs already in QUERY_ROLES')

# Step2: SHORT_SETUP_15m を active に戻す
import sqlite3
c = sqlite3.connect('registry.db')
c.execute("UPDATE strategies SET status='active' WHERE title='SHORT_SETUP_15m'")
c.commit()
print('OK - SHORT_SETUP_15m reset to active')

# Step3: 重複している SHORT_INSTANT_4H を1件削除
rows = c.execute("SELECT rowid FROM strategies WHERE title='SHORT_INSTANT_4H'").fetchall()
if len(rows) > 1:
    c.execute("DELETE FROM strategies WHERE rowid=?", (rows[0][0],))
    c.commit()
    print(f'OK - duplicate SHORT_INSTANT_4H removed')

print('\n=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()

# Step4: QUERY_ROLES確認
print('\n=== QUERY_ROLES (lines 7-30) ===')
with open('elfa_grvt_bot/strategy_engine.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(6, min(len(lines), 30)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
