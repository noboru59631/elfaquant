"""check_login_response.py - ログインレスポンスの完全な構造を確認"""
import asyncio, pathlib, json, httpx

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://edge.grvt.io/auth/api_key/login",
            json={"api_key": env.get("GRVT_TRADING_API_KEY", "")},
        )
        print(f"Status: {r.status_code}")
        print("\n=== Headers (関連部分) ===")
        for k, v in r.headers.items():
            if any(x in k.lower() for x in ["cookie", "account", "grvt"]):
                print(f"  {k}: {v}")
        print("\n=== Response JSON ===")
        try:
            data = r.json()
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"JSON parse error: {e}")
            print(r.text[:500])

asyncio.run(main())
