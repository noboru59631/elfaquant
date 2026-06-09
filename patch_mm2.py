with open('mm_bot.py', encoding='utf-8') as f:
    lines = f.readlines()

# 90行目 (index 89) のインデントを修正
for i, l in enumerate(lines):
    if l.strip() == 'post_only=True,' and not l.startswith('            '):
        lines[i] = '            post_only=True,\n'
        print(f'{i+1}行目のインデントを修正しました')

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
