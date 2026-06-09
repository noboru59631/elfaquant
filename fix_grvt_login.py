with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# place_entry_with_tpsl の直前にloginを追加
old = """        # 8. Place order
        try:
            result = await self.grvt.place_entry_with_tpsl("""

new = """        # 8. Place order
        try:
            # Ensure authenticated before placing order
            if not self.grvt.cookie:
                login_ok = await self.grvt.login()
                if not login_ok:
                    await self.finalize_failure(
                        event_id, query_id, 'grvt_error', 'grvt_auth_failed',
                        'GRVT login() returned False')
                    return
            result = await self.grvt.place_entry_with_tpsl("""

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - grvt login fix applied')
else:
    print('ERROR: pattern not found')

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== core.py lines 280-300 ===')
for i in range(279, 300):
    print(f'{i+1:03}: {lines[i].rstrip()}')
