import asyncio, pathlib, time, random
from decimal import Decimal
import httpx
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

ENTRY      = 74497.5
SIZE       = Decimal("0.02")
SL_TRIGGER = round(ENTRY * 1.015, 1)
SL_LIMIT   = round(ENTRY * 1.05,  1)

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()
    print(f"Login OK - cookie: {grvt.cookie[:20]}...")
    print(f"SL trigger: ${SL_TRIGGER:,.1f}  limit: ${SL_LIMIT:,.1f}")

    nonce           = random.randint(0, 4294967295)
    client_order_id = random.getrandbits(64)
    exp_ns          = str(int((time.time() + 86400 * 29) * 1_000_000_000))

    sig = grvt._sign_order(
        sub_account_id    = "7643292000705847",
        client_order_id   = client_order_id,
        time_in_force_int = 1,
        instrument        = "BTC_USDT_Perp",
        size_str          = str(SIZE),
        limit_price_str   = str(SL_LIMIT),
        is_buying         = True,
        nonce             = nonce,
        expiration_ns     = exp_ns,
        is_market         = False,
        post_only         = False,
        reduce_only       = True,
    )

    payload = {
        "sub_account_id": "7643292000705847",
        "is_market": False,
        "time_in_force": "GOOD_TILL_TIME",
        "post_only": False,
        "reduce_only": True,
        "legs": [{"instrument": "BTC_USDT_Perp", "size": str(SIZE),
                  "limit_price": str(SL_LIMIT), "is_buying_asset": True}],
        "signature": sig,
        "metadata": {"client_order_id": str(client_order_id)},
        "trigger": {
            "trigger_type": "STOP_LOSS",
            "tpsl": {
                "trigger_by": "MARK",
                "trigger_price": str(SL_TRIGGER),
                "close_position": False
            }
        }
    }

    # 同じhttpxセッション内でリクエスト送信
    async with httpx.AsyncClient(timeout=15) as client:
        # 再ログインして新鮮なcookieを取得
        login_r = await client.post(
            "https://edge.grvt.io/auth/api_key/login",
            json={"api_key": env.get("GRVT_TRADING_API_KEY","")},
            headers={"Content-Type": "application/json"}
        )
        fresh_cookie = login_r.cookies.get("gravity", "")
        print(f"Fresh cookie: {fresh_cookie[:20]}...")

        r = await client.post(
            "https://trades.grvt.io/full/v1/create_order",
            json=payload,
            cookies={"gravity": fresh_cookie}
        )
        print(f"Status: {r.status_code}")
        print(r.text[:600])

asyncio.run(main())
