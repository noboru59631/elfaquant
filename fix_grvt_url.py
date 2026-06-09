with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    content = f.read()

# fetch_mid_price メソッドを完全置換
old = '''    async def fetch_mid_price(self, symbol: str) -> Decimal:
        """
        Fetch mid price for a symbol
        """
        try:
            response = await self.client.get(
                f"https://market-data.grvt.io/full/v1/mini_ticker?instrument={symbol}"
            )
            response.raise_for_status()
            data = response.json()

            if "mark_price" in data and data["mark_price"]:
                return Decimal(str(data["mark_price"]))
            elif "best_bid" in data and "best_ask" in data:
                return (Decimal(str(data["best_bid"])) + Decimal(str(data["best_ask"]))) / 2
            else:
                raise ValueError("Could not determine mid price from ticker data")

        except Exception as e:
            raise ValueError(f"Failed to fetch mid price: {str(e)}")'''

new = '''    async def fetch_mid_price(self, symbol: str) -> Decimal:
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
            raise ValueError(f"Failed to fetch mid price: {str(e)}")'''

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - fetch_mid_price fixed')
else:
    print('ERROR: pattern not found, showing current fetch_mid_price:')
    for i, line in enumerate(content.splitlines()):
        if 'fetch_mid' in line or 'grvt.io' in line or 'market-data' in line:
            print(f'  {i+1}: {line}')
