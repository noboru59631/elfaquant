with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

start = content.find('async def place_market_close')
end = content.find('\nasync def ', start + 1)
print("=== 現在のplace_market_close ===")
print(content[start:end])
