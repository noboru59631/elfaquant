with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# await self.registry.update_strategy_status -> self.registry.update_strategy_status
old = 'await self.registry.update_strategy_status(query_id, new_status)'
new = 'self.registry.update_strategy_status(query_id, new_status)'

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - await removed from update_strategy_status')
else:
    print('Pattern not found, checking line 322:')
    for i, line in enumerate(content.splitlines()[318:328], start=319):
        print(f'{i}: {repr(line)}')
