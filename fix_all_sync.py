with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# get_strategy の await を除去
content = content.replace(
    'strategy = await self.registry.get_strategy(query_id)',
    'strategy = self.registry.get_strategy(query_id)'
)

# update_strategy_status の await を除去（残っていれば）
content = content.replace(
    'await self.registry.update_strategy_status(',
    'self.registry.update_strategy_status('
)

# add_fire の await を除去（残っていれば）
content = content.replace(
    'await self.registry.add_fire(',
    'self.registry.add_fire('
)

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK - all sync fixes applied')

# process_fire 周辺確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
print()
print('=== Lines 178-195 (process_fire) ===')
for i in range(177, min(len(lines), 196)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
