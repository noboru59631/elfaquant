with open('mm_bot_v7.py', encoding='utf-8') as f:
    content = f.read()

# 残高取得キーを修正
content = content.replace(
    'start_balance = Decimal(str(acct.get("total_equity", 0)))',
    'start_balance = Decimal(str(acct.get("total_equity", 0) or acct.get("totalEquity", 0) or 0))'
)

# equity取得も修正
content = content.replace(
    'equity = Decimal(str(acct.get("total_equity", 0)))',
    'equity = Decimal(str(acct.get("total_equity", 0) or acct.get("totalEquity", 0) or start_balance))'
)

with open('mm_bot_v7.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ 残高取得修正完了")
