with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# sync_terminal_statusの呼び出しをスキップ
old = '            await self.sync_terminal_status(query_id, remote_status, executions)'
new = '            # sync_terminal_status disabled to prevent infinite loop\n            pass  # await self.sync_terminal_status(query_id, remote_status, executions)'

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - sync_terminal_status disabled')
else:
    print('Pattern not found, searching...')
    for i, line in enumerate(content.splitlines()):
        if 'sync_terminal_status' in line:
            print(f'{i+1}: {repr(line)}')
