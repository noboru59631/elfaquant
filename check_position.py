import asyncio, pathlib, httpx, json

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        # Login first
        r = await client.post(
            "https://edge.grvt.io/auth/api_key/login",
            json={"api_key": env.get("GRVT_TRADING_API_KEY", "")},
            headers={"Content-Type": "application/json"}
        )
        cookie = r.cookies.get("gravity", "")
        
        # Get open positions
        r2 = await client.post(
            "https://trades.grvt.io/full/v1/account_summary",
            json={"sub_account_id": "7643292000705847"},
            cookies={"gravity": cookie}
        )
        print(f"Status: {r2.status_code}")
        print(json.dumps(r2.json(), indent=2))

asyncio.run(main())
