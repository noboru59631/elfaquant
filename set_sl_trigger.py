import asyncio, pathlib, random, time
from decimal import Decimal
import httpx
from elfa_grvt_bot.grvt_client import GrvtClient

env = {k.strip(): v.strip() for line in pathlib.Path('.env').read_text().splitlines()
       if '=' in line and not line.startswith('#')
       for k, v in [line.split('=', 1)]}

ENTRY = 74578.0
SIZE  = Decimal("0.02")
SL    = round(ENTRY * 1.015, 1)
SL_LIMIT = round(SL * 1.005, 1)

async def main():
    grvt = GrvtClient(env.get("GRVT_TRADING_API_KEY",""), env.get("GRVT_TRADING_PRIVATE_KEY",""))
    await grvt.login()
    print(f"Login OK: {grvt.account_id}")
    print(f"SL trigger: ${SL:,.1f}  limit: ${SL_LIMIT:,.1f}")

    nonce           = random.randint(1, 2**31 - 1)
    expiration_ns   = str((int(time.time()) + 29 * 86400) * 1_000_000_000)
    client_order_id = random.getrandbits(64)

    sig = grvt._sign_order(
        sub_account_id    = grvt.account_id,
        client_order_id   = client_order_id,
        time_in_force_int = 1,
        instrument        = "BTC_USDT_Perp",
        size_str          = str(SIZE),
        limit_price_str   = str(SL_LIMIT),
        is_buying         = True,
        nonce             = nonce,
        expiration_ns     = expiration_ns,
        is_market         = False,
        reduce_only       = True,
    )

    payload = {
        "order": {
            "sub_account_id": grvt.account_id,
            "is_market":      False,
            "time_in_force":  "GOOD_TILL_TIME",
            "post_only":      False,
            "reduce_only":    True,
            "legs": [{
                "instrument":      "BTC_USDT_Perp",
                "size":            str(SIZE),
                "limit_price":     str(SL_LIMIT),
                "is_buying_asset": True,
            }],
            "signature": sig,
            "metadata": {"client_order_id": str(client_order_id)},
            "trigger": {
                "trigger_type": "STOP_LOSS",
                "tpsl": {
                    "trigger_by":     "MARK",
                    "trigger_price":  str(SL),
                    "close_position": False,
                }
            }
        }
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://trades.grvt.io/full/v1/create_order",
            json=payload,
            cookies={"gravity": grvt.cookie},
            headers={"Content-Type": "application/json"},
        )
        print(f"HTTP {r.status_code}: {r.text[:300]}")

    await grvt.close()

asyncio.run(main())
