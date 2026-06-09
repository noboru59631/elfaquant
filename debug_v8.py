import asyncio, aiohttp, os, time
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

API_KEY     = os.getenv("GRVT_TRADING_API_KEY", "")
PRIVATE_KEY = os.getenv("GRVT_PRIVATE_KEY", "")
CHAIN_URL   = "https://edge.api.grvt.io"
BASE_URL    = "https://trades.grvt.io"

print(f"API_KEY     = '{API_KEY[:8]}...' (長さ:{len(API_KEY)})")
print(f"PRIVATE_KEY = '{PRIVATE_KEY[:8]}...' (長さ:{len(PRIVATE_KEY)})")

async def test():
    async with aiohttp.ClientSession() as session:
        # ログインテスト
        print("\n--- ログイン試行 ---")
        url = f"{CHAIN_URL}/auth/api_key/login"
        payload = {"api_key": API_KEY}
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                text = await r.text()
                print(f"ステータス: {r.status}")
                print(f"レスポンス: {text[:300]}")
                cookie = r.cookies.get("gravity")
                print(f"Cookie: {cookie}")
        except Exception as e:
            print(f"❌ 例外: {e}")

asyncio.run(test())
