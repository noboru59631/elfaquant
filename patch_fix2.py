with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'bal2, pos2 = await get_account_data(grvt)',
    'bal2, pos2, _ = await get_account_data(grvt)'
)
print("修正完了" if 'bal2, pos2, _ = await get_account_data(grvt)' in content else "修正失敗")

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
