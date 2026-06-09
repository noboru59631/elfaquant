# emergency_fix_core.py
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

old = '''        import logging as _logging
        self.logger = _logging.getLogger(__name__)
        self.registry = registry
        self.elfa = elfa_client
        self.grvt = grvt_client
        self.alerts = alerts'''

new = '''        import logging as _logging
        self.logger = _logging.getLogger(__name__)
        self.registry = registry
        self.elfa = elfa_client
        self.grvt = grvt_client
        self.alerts = alerts
        self._last_fired: dict = {}
        self._cooldown_sec: int = 4 * 3600'''

if old in content:
    content = content.replace(old, new, 1)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK - _last_fired added to __init__")
else:
    print("ERROR: pattern not found")
    # フォールバック: hasattrガードを追加
    old2 = '''        import time as _time
        now_ts = _time.time()
        last = self._last_fired.get(query_id, 0)'''
    new2 = '''        import time as _time
        now_ts = _time.time()
        if not hasattr(self, '_last_fired'):
            self._last_fired = {}
        if not hasattr(self, '_cooldown_sec'):
            self._cooldown_sec = 4 * 3600
        last = self._last_fired.get(query_id, 0)'''
    if old2 in content:
        content = content.replace(old2, new2, 1)
        with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("OK - fallback hasattr guard added")
    else:
        print("ERROR: fallback also failed - manual fix needed")

# 結果確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'def __init__' in l:
        for j in range(i, min(i+12, len(lines))):
            print(f"{j+1:03}: {lines[j].rstrip()}")
        break
