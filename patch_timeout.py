with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

old = 'LONELY_SEC     = 30          # 片側約定後の待機秒数'
new = 'LONELY_SEC     = 30          # 片側約定後の待機秒数\nMAKER_CLOSE_TIMEOUT = 60     # Maker指値クローズの待機秒数'

if old in content:
    content = content.replace(old, new)
    print("定数追加完了")
else:
    print("パターンが見つかりません")

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
