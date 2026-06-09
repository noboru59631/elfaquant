with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

old = "            active = self.registry.list_strategies(status='active')"

new = """            # Auto-reset fired strategies back to active
            import sqlite3 as _sq
            _c = _sq.connect('registry.db')
            _fired = _c.execute("SELECT count(*) FROM strategies WHERE status='fired'").fetchone()[0]
            if _fired > 0:
                _c.execute("UPDATE strategies SET status='active' WHERE status='fired'")
                _c.commit()
                import logging as _log
                _log.getLogger(__name__).info(f'[Supervisor] Auto-reset {_fired} fired strategies to active')
            _c.close()

            active = self.registry.list_strategies(status='active')"""

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - auto-reset patch applied')
else:
    print('ERROR: pattern not found')
    for i, line in enumerate(content.splitlines()):
        if 'list_strategies' in line:
            print(f'{i+1}: {line}')
