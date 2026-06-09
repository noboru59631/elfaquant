with open('mm_bot.py', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines[284:298]):
    print(f'{i+285:03}: {l.rstrip()}')
