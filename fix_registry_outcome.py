"""fix_registry_outcome.py - update_fire_outcome に全引数を追加"""

with open('elfa_grvt_bot/registry.py', encoding='utf-8') as f:
    content = f.read()

old = '''    def update_fire_outcome(self, event_id: str, outcome: str, error: str = None) -> bool:
        try:
            self._conn.execute(
                "UPDATE fires SET outcome=?, error=?, updated_at=datetime('now') WHERE event_id=?",
                (outcome, error, event_id)
            )
            self._conn.commit()
            return True
        except Exception:
            return False'''

new = '''    def update_fire_outcome(
        self,
        event_id: str,
        outcome: str,
        error: str = None,
        parent_order_id: str = None,
        tp_order_id: str = None,
        sl_order_id: str = None,
        reference_price: float = None,
        tp_price: float = None,
        sl_price: float = None,
    ) -> bool:
        try:
            self._conn.execute(
                """UPDATE fires SET
                    outcome=?,
                    error=?,
                    parent_order_id=?,
                    tp_order_id=?,
                    sl_order_id=?,
                    reference_price=?,
                    tp_price=?,
                    sl_price=?,
                    placed_at=CASE WHEN ? IS NOT NULL THEN datetime('now') ELSE placed_at END
                WHERE event_id=?""",
                (
                    outcome,
                    error,
                    parent_order_id,
                    tp_order_id,
                    sl_order_id,
                    reference_price,
                    tp_price,
                    sl_price,
                    parent_order_id,
                    event_id,
                )
            )
            self._conn.commit()
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"update_fire_outcome error: {e}")
            return False'''

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/registry.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - update_fire_outcome fixed')
else:
    print('ERROR: pattern not found, trying regex...')
    import re
    pattern = re.compile(
        r'def update_fire_outcome\(self, event_id: str, outcome: str, error: str = None\) -> bool:.*?return False',
        re.DOTALL
    )
    if pattern.search(content):
        content = pattern.sub(new.strip(), content)
        with open('elfa_grvt_bot/registry.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('OK - regex fix applied')
    else:
        print('ERROR: regex also failed')

# 確認
with open('elfa_grvt_bot/registry.py', encoding='utf-8') as f:
    lines = f.readlines()
print(f'\nTotal lines: {len(lines)}')
for i, l in enumerate(lines):
    if 'def update_fire_outcome' in l:
        for j in range(i, min(i+35, len(lines))):
            print(f'{j+1:03}: {lines[j].rstrip()}')
        break
