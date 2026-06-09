import pathlib
text = pathlib.Path('mm_bot_v7.py').read_text(encoding='utf-8')
# 先頭200行を表示
lines = text.splitlines()
for i, line in enumerate(lines[:200]):
    print(f"{i+1:3}: {line}")
