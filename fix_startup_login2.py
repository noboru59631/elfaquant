with open('elfa_grvt_bot/cli.py', encoding='utf-8') as f:
    lines = f.readlines()

# line 131 の後 (index 131) にログインコードを挿入
# 現在: 131: core = Core(...)
# 132: (空行)
# 133: try:

insert_pos = None
for i, line in enumerate(lines):
    if 'core = Core(registry, elfa, grvt, alerts)' in line:
        insert_pos = i + 1
        break

if insert_pos is None:
    print('ERROR: core = Core(...) not found')
else:
    login_code = [
        '\n',
        '    # Login to GRVT at startup\n',
        '    import logging as _lg\n',
        '    _logger = _lg.getLogger(__name__)\n',
        '    try:\n',
        '        login_ok = await grvt.login()\n',
        '        if login_ok:\n',
        '            _logger.info(f"[GRVT] Login successful - account_id: {grvt.account_id}")\n',
        '        else:\n',
        '            _logger.error("[GRVT] Login failed")\n',
        '    except Exception as _login_err:\n',
        '        _logger.error(f"[GRVT] Login error: {_login_err}")\n',
    ]
    lines = lines[:insert_pos] + login_code + lines[insert_pos:]
    with open('elfa_grvt_bot/cli.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f'OK - login code inserted after line {insert_pos}')

# 確認
with open('elfa_grvt_bot/cli.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== cli.py lines 130-155 ===')
for i in range(129, 155):
    print(f'{i+1:03}: {lines[i].rstrip()}')
