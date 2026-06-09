with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

print('=== process_fire / on_event 関連行 ===')
for i, line in enumerate(lines):
    if any(kw in line for kw in ['process_fire', 'on_event', 'engine_eval', 'ENTER_', 'place_order', 'grvt', 'decision']):
        print(f'{i+1:03}: {line.rstrip()}')

print()
print('=== Lines 94-130 (triggered処理周辺) ===')
for i in range(93, min(len(lines), 131)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
