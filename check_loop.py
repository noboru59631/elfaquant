with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

print('=== Lines 88-115 (strategy_loop) ===')
for i in range(87, min(len(lines), 116)):
    print(f'{i+1:03}: {lines[i].rstrip()}')

print()
print('=== Lines 318-345 (sync_terminal_status) ===')
for i in range(317, min(len(lines), 346)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
