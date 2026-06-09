with open('mm_bot.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'async def place_limit' in l:
        # place_limit関数のreduce_only行を探してpost_only追加
        for j in range(i, i+20):
            if 'reduce_only=False,' in lines[j]:
                lines[j] = lines[j].rstrip('\n') + '\n'
                lines.insert(j+1, '        post_only=True,\n')
                print(f'{j+1}行目の後にpost_only=Trueを追加')
                break
        break

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
