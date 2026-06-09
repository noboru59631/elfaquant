"""add_cooldown.py - 同一ストラテジーの再発火を4時間ブロックするクールダウン機能を追加"""
import re

with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# __init__にクールダウン辞書を追加
old_init = '''        self.logger = logging.getLogger(__name__)'''
new_init = '''        self.logger = logging.getLogger(__name__)
        self._last_fired: dict = {}          # query_id -> last fired timestamp
        self._cooldown_sec: int = 4 * 3600  # 4時間クールダウン'''

# トリガー処理の先頭にクールダウンチェックを追加
old_trigger = '''        strategy = self.registry.get_strategy(query_id)
        if not strategy:
            self.registry.update_fire_outcome(event_id, 'unknown_strategy','''

new_trigger = '''        # ── クールダウンチェック ──────────────────────────
        import time as _time
        now_ts = _time.time()
        last = self._last_fired.get(query_id, 0)
        elapsed = now_ts - last
        if elapsed < self._cooldown_sec:
            remaining = int(self._cooldown_sec - elapsed)
            self.logger.info(
                f"[Cooldown] {query_id[:8]} skipped - "
                f"{remaining//3600}h{(remaining%3600)//60}m remaining"
            )
            return
        # ─────────────────────────────────────────────────

        strategy = self.registry.get_strategy(query_id)
        if not strategy:
            self.registry.update_fire_outcome(event_id, 'unknown_strategy','''

# 発火成功時にタイムスタンプを記録
old_success = '''            # 9. Record success
            self.registry.update_fire_outcome('''
new_success = '''            # 9. Record success
            import time as _time
            self._last_fired[query_id] = _time.time()
            self.registry.update_fire_outcome('''

results = []
for old, new, label in [
    (old_init,    new_init,    "__init__ cooldown dict"),
    (old_trigger, new_trigger, "cooldown check"),
    (old_success, new_success, "fired timestamp record"),
]:
    if old in content:
        content = content.replace(old, new, 1)
        results.append(f"OK - {label}")
    else:
        results.append(f"WARNING - pattern not found: {label}")

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.write(content)

for r in results:
    print(r)

# 確認表示
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
print(f"\nTotal lines: {len(lines)}")
for i, l in enumerate(lines):
    if 'Cooldown' in l or 'cooldown' in l or '_last_fired' in l:
        print(f"{i+1:03}: {l.rstrip()}")
