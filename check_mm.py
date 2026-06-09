with open('mm_bot.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'my_bid' in l or 'my_ask' in l:
        print(f'{i+1:03}: {l.rstrip()}')
