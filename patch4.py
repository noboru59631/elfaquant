with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

# _place_single_order 内の _sign_order 呼び出しに post_only を追加
# "reduce_only       = reduce_only," の次の行に追加
for i, l in enumerate(lines):
    if 'reduce_only       = reduce_only,' in l and i > 190:
        # この行の後に post_only を挿入
        lines[i] = lines[i].rstrip() + '\n'
        lines.insert(i + 1, '            post_only       = post_only,\n')
        print(f'{i+1}行目の後に post_only を追加しました')
        break

with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
