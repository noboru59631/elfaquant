import re

with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

# market_close_all関数を探して全文表示（確認用）
start = content.find('async def market_close_all')
end = content.find('\nasync def ', start + 1)
print("=== 現在のmarket_close_all ===")
print(content[start:end])
