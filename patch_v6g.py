with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

# MAX_INV超過時の呼び出し
content = content.replace(
    'await market_close_all(grvt, "MAX_INV")',
    'await market_close_all(grvt, "MAX_INV", mid)'
)

# STOP_LOSS時の呼び出し
content = content.replace(
    'await market_close_all(grvt, "STOP_LOSS")',
    'await market_close_all(grvt, "STOP_LOSS", mid)'
)

# DAILY_LIMIT時の呼び出し
content = content.replace(
    'await market_close_all(grvt, "DAILY_LIMIT")',
    'await market_close_all(grvt, "DAILY_LIMIT", mid)'
)

with open('mm_bot_v6.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 検証
checks = [
    'market_close_all(grvt, "MAX_INV", mid)',
    'market_close_all(grvt, "STOP_LOSS", mid)',
    'market_close_all(grvt, "DAILY_LIMIT", mid)',
]
all_ok = True
for c in checks:
    ok = c in content
    print(f"{'✅' if ok else '❌'} {c}")
    if not ok:
        all_ok = False

print()
print("✅ 全修正完了 — ボット再起動可能です" if all_ok else "❌ 一部失敗")
