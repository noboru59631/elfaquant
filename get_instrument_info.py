"""get_instrument_info.py - BTC_USDT_Perpのinstrument_hashとbase_decimalsを取得"""
import asyncio, httpx, json

async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        # instruments一覧を取得
        r = await client.post(
            "https://market-data.grvt.io/full/v1/instrument",
            json={"instrument": "BTC_USDT_Perp"},
        )
        print(f"Status: {r.status_code}")
        print("=== Response ===")
        try:
            data = r.json()
            print(json.dumps(data, indent=2))
        except:
            print(r.text[:500])

asyncio.run(main())
