with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

# 103行目 (index 102) の重複 post_only を削除
del lines[102]

with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('修正完了')
