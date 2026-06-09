with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

# get_account_dataはdictを返すので、positionを直接取得する
old = '                    bal2, pos2, _ = await get_account_data(grvt)'
new = '''                    acct2 = await get_account_data(grvt)
                    pos_list2 = acct2.get("open_positions", [])
                    pos2 = Decimal(str(pos_list2[0]["size"])) if pos_list2 else Decimal("0")'''

if old in content:
    content = content.replace(old, new)
    print("修正完了")
else:
    print("パターンが見つかりません - 現在の行を確認")
    for i, line in enumerate(content.split('\n')):
        if 'bal2' in line or 'pos2' in line:
            print(f"{i+1}: {line}")

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
