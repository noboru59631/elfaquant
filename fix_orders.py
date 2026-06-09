"""fix_orders.py - 余分なTP注文をキャンセルし、正しいTP/SLを1つずつ残す"""
import asyncio, pathlib, httpx, json
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

# 現在のポジション
POSITION_SIZE = 0.022   # BTC ショートポジション
SYMBOL = "BTC_USDT_Perp"
SUB_ACCOUNT_ID = "7643292000705847"

async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        # Login
        r = await client.post(
            "https://edge.grvt.io/auth/api_key/login",
            json={"api_key": env.get("GRVT_TRADING_API_KEY", "")},
            headers={"Content-Type": "application/json"}
        )
        cookie = r.cookies.get("gravity", "")
        print(f"Login: {r.status_code}")

        # 現在のオープン注文取得
        r2 = await client.post(
            "https://trades.grvt.io/full/v1/open_orders",
            json={"sub_account_id": SUB_ACCOUNT_ID},
            cookies={"gravity": cookie}
        )
        result = r2.json().get("result", [])
        orders = result if isinstance(result, list) else result.get("orders", [])

        # BTC TPを抽出してソート（limit_price 昇順 = 最も低いTPを1つ残す）
        btc_tp = [o for o in orders
                  if o.get("legs", [{}])[0].get("instrument") == SYMBOL
                  and o.get("reduce_only") == True
                  and o.get("legs", [{}])[0].get("is_buying_asset") == True]

        print(f"\nBTC TP注文数: {len(btc_tp)}")

        # limit_price 昇順ソート（最も低い価格 = 最も早く約定するTPを残す）
        btc_tp.sort(key=lambda o: float(o.get("legs", [{}])[0].get("limit_price", "99999")))

        # 残すTP: 最初の1つ（最も低い価格）、残りはキャンセル
        keep = btc_tp[0] if btc_tp else None
        cancel_list = btc_tp[1:] if len(btc_tp) > 1 else []

        if keep:
            leg = keep.get("legs", [{}])[0]
            print(f"\n✅ 残すTP: size={leg.get('size')} @ {leg.get('limit_price')} order_id={keep.get('order_id','')[:24]}")

        print(f"❌ キャンセルするTP: {len(cancel_list)}件")

        # キャンセル実行
        for o in cancel_list:
            oid = o.get("order_id")
            leg = o.get("legs", [{}])[0]
            r3 = await client.post(
                "https://trades.grvt.io/full/v1/cancel_order",
                json={
                    "sub_account_id": SUB_ACCOUNT_ID,
                    "order_id": oid
                },
                cookies={"gravity": cookie}
            )
            print(f"  キャンセル {oid[:24]} @ {leg.get('limit_price')} → HTTP {r3.status_code}: {r3.text[:80]}")

        # XAU TPは現在ポジションあり(-0.02)なので残す
        xau_tp = [o for o in orders
                  if o.get("legs", [{}])[0].get("instrument") == "XAU_USDT_Perp"]
        print(f"\nXAU注文数: {len(xau_tp)} (ポジションあるため維持)")

        print("\n=== 完了 ===")
        print(f"BTC TP: {len(cancel_list)}件キャンセル、1件維持")
        print(f"次にBTC SLを新規配置してください")

asyncio.run(main())
