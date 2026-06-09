with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

# 現在の fetch_mid_price を表示
print('=== 現在の fetch_mid_price (lines 45-65) ===')
for i in range(44, min(len(lines), 66)):
    print(f'{i+1:03}: {lines[i].rstrip()}')

# 新しい fetch_mid_price で全体を置換
new_method = '''    async def fetch_mid_price(self, symbol: str) -> Decimal:
        """
        Fetch mid price for a symbol using GRVT mini ticker API (POST)
        """
        try:
            response = await self.client.post(
                "https://market-data.grvt.io/full/v1/mini",
                json={"instrument": symbol}
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("result", data)

            if result.get("mark_price"):
                return Decimal(str(result["mark_price"]))
            elif result.get("mid_price"):
                return Decimal(str(result["mid_price"]))
            elif result.get("best_bid_price") and result.get("best_ask_price"):
                return (Decimal(str(result["best_bid_price"])) + Decimal(str(result["best_ask_price"]))) / 2
            elif result.get("last_price"):
                return Decimal(str(result["last_price"]))
            else:
                raise ValueError(f"Could not determine mid price. Response: {data}")

        except Exception as e:
            raise ValueError(f"Failed to fetch mid price: {str(e)}")
'''

# line 45 から except まで検索して置換
start = None
end = None
for i, line in enumerate(lines):
    if 'async def fetch_mid_price' in line:
        start = i
    if start and i > start and line.strip().startswith('async def ') and i > start + 1:
        end = i
        break

if start is None:
    print('ERROR: fetch_mid_price not found')
else:
    if end is None:
        # 次のメソッドまで探す
        for i in range(start + 1, len(lines)):
            if lines[i].strip().startswith('async def ') or lines[i].strip().startswith('def '):
                end = i
                break

    print(f'\nReplacing lines {start+1} to {end}')
    new_lines = lines[:start] + [new_method + '\n'] + lines[end:]
    with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('OK - fetch_mid_price replaced')

    # 確認
    with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
        lines2 = f.readlines()
    print()
    print('=== 修正後 (lines 45-72) ===')
    for i in range(44, min(len(lines2), 73)):
        print(f'{i+1:03}: {lines2[i].rstrip()}')
