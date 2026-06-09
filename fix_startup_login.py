with open('elfa_grvt_bot/cli.py', encoding='utf-8') as f:
    content = f.read()

old = """    core = Core(registry, elfa, grvt, alerts)

    try:
        await core.supervisor()"""

new = """    core = Core(registry, elfa, grvt, alerts)

    # Login to GRVT at startup
    import logging as _lg
    _logger = _lg.getLogger(__name__)
    try:
        login_ok = await grvt.login()
        if login_ok:
            _logger.info(f'[GRVT] Login successful - account_id: {grvt.account_id}')
        else:
            _logger.error('[GRVT] Login failed - orders will not be placed')
    except Exception as _login_err:
        _logger.error(f'[GRVT] Login error: {_login_err}')

    try:
        await core.supervisor()"""

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/cli.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - startup login added to cli.py')
else:
    print('ERROR: pattern not found')

# 確認
with open('elfa_grvt_bot/cli.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== cli.py lines 125-150 ===')
for i in range(124, 150):
    print(f'{i+1:03}: {lines[i].rstrip()}')
