import asyncio, pathlib, httpx, json

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        # Login
        r = await client.post(
            "https://edge.grvt.io/auth/api_key/login",
            json={"api_key": env.get("GRVT_TRADING_API_KEY", "")},
            headers={"Content-Type": "application/json"}
        )
        cookie = r.cookies.get("gravity", "")

        # Get open orders
        r2 = await client.post(
            "https://trades.grvt.io/full/v1/open_orders",
            json={"sub_account_id": "7643292000705847"},
            cookies={"gravity": cookie}
        )
        print(f"Status: {r2.status_code}")
        data = r2.json()

        # result がリストの場合もオブジェクトの場合も対応
        result = data.get("result", [])
        if isinstance(result, dict):
            orders = result.get("orders", [])
        elif isinstance(result, list):
            orders = result
        else:
            orders = []

        print(f"オープン注文数: {len(orders)}")
        print("=" * 60)
        for o in orders:
            legs = o.get("legs", [{}])
            leg = legs[0] if legs else {}
            meta = o.get("metadata", {})
            state = o.get("state", {})
            print(f"order_id     : {str(o.get('order_id',''))[:24]}")
            print(f"instrument   : {leg.get('instrument','')}")
            size_dir = 'BUY' if leg.get('is_buying_asset') else 'SELL'
            print(f"size         : {leg.get('size','')} {size_dir}")
            lp = leg.get('limit_price', '')
            print(f"limit_price  : {lp if lp and lp != '0' else '(market)'}")
            print(f"reduce_only  : {o.get('reduce_only','')}")
            print(f"time_in_force: {o.get('time_in_force','')}")
            print(f"status       : {state.get('status','')}")
            print(f"client_id    : {meta.get('client_order_id','')}")
            print("-" * 40)

        if not orders:
            print("オープン注文なし")
            print("\n=== RAW response (参考) ===")
            print(json.dumps(data, indent=2)[:800])

asyncio.run(main())
