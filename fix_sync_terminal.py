with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# awaitを全て除去: sync_terminal_statusメソッド内のregistry呼び出し
replacements = [
    ('await self.registry.add_fire(', 'self.registry.add_fire('),
    ('await self.registry.update_strategy_status(', 'self.registry.update_strategy_status('),
    ('await self.registry.fire_exists(', 'self.registry.fire_exists('),
]

count = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print('Fixed: ' + old[:50])
        count += 1

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Total fixes:', count)

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(318, min(len(lines), 345)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
