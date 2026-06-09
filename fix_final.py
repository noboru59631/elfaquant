# ========== 1. registry.py に update_fire_outcome を追加 ==========
with open('elfa_grvt_bot/registry.py', encoding='utf-8') as f:
    reg_content = f.read()

new_method = '''
    def update_fire_outcome(self, event_id: str, outcome: str, error: str = None) -> bool:
        try:
            self._conn.execute(
                "UPDATE fires SET outcome=?, error=?, updated_at=datetime('now') WHERE event_id=?",
                (outcome, error, event_id)
            )
            self._conn.commit()
            return True
        except Exception:
            return False
'''

# list_strategies の前に挿入
insert_before = '    def list_strategies('
if insert_before in reg_content and 'update_fire_outcome' not in reg_content:
    reg_content = reg_content.replace(insert_before, new_method + '    def list_strategies(')
    with open('elfa_grvt_bot/registry.py', 'w', encoding='utf-8') as f:
        f.write(reg_content)
    print('OK - update_fire_outcome added to registry.py')
else:
    print('SKIP registry - already exists or pattern not found')

# ========== 2. grvt_client.py の fetch_mid_price URL を修正 ==========
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    grvt_content = f.read()

old_url = 'f"https://market-data.grvt.io/market-data/v1/instruments/{symbol}/ticker"'
new_url = 'f"https://market-data.grvt.io/full/v1/mini_ticker?instrument={symbol}"'

if old_url in grvt_content:
    grvt_content = grvt_content.replace(old_url, new_url)
    with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
        f.write(grvt_content)
    print('OK - grvt_client URL fixed')
else:
    print('SKIP grvt_client - pattern not found, showing current URLs:')
    for i, line in enumerate(grvt_content.splitlines()):
        if 'grvt.io' in line or 'market-data' in line:
            print(f'  {i+1}: {line}')

# ========== 3. fetch_mid_price のレスポンス解析も修正 ==========
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

print()
print('=== grvt_client.py fetch_mid_price (lines 44-70) ===')
for i in range(43, min(len(lines), 71)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
