with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# Auto-resetブロックを無効化
old = '''# Auto-reset fired strategies back to active
                import sqlite3 as _sq
                _c = _sq.connect('registry.db')
                _fired = _c.execute("SELECT count(*) FROM strategies WHERE status='fired'").fetchone()[0]
                if _fired > 0:
                    _c.execute("UPDATE strategies SET status='active' WHERE status='fired'")
                    _c.commit()
                    import logging as _log
                    _log.getLogger(__name__).info(f'[Supervisor] Auto-reset {_fired} fired strategies to active')
                _c.close()'''

new = '''# Auto-reset DISABLED - fired strategies stay fired'''

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - auto-reset disabled')
else:
    # パターンが違う場合は行番号で探す
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'Auto-reset' in line and 'fired' in line:
            print(f'{i+1:03}: {line}')
    print('ERROR: pattern not found - check lines above')
