"""
rebuild_grvt_client.py
grvt_client.py を GRVT API 仕様に合わせて完全に書き直す
"""

NEW_CONTENT = r'''"""
GRVT trading client - EIP-712 signed orders
API: https://api-docs.grvt.io/trading_api/
"""
import time
import random
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)

GRVT_CHAIN_ID  = "325"
GRVT_LOGIN_URL = "https://edge.grvt.io/auth/api_key/login"
GRVT_MARKET_URL= "https://market-data.grvt.io/full/v1/mini"
GRVT_ORDER_URL = "https://trades.grvt.io/full/v1/create_order"


class GrvtClient:
    def __init__(self, api_key: str, private_key: str):
        self.api_key     = api_key
        self.private_key = private_key
        self.account_id: Optional[str] = None
        self.cookie:     Optional[str] = None
        self.client = httpx.AsyncClient(timeout=15)

    async def login(self) -> bool:
        try:
            r = await self.client.post(
                GRVT_LOGIN_URL,
                json={"api_key": self.api_key},
                timeout=15,
            )
            r.raise_for_status()
            cookie_header = r.headers.get("set-cookie", "")
            for part in cookie_header.split(";"):
                part = part.strip()
                if part.startswith("gravity="):
                    self.cookie = part.split("=", 1)[1]
                    break
            if not self.cookie:
                raise ValueError("gravity cookie not found")
            data = r.json()
            self.account_id = str(
                data.get("result", {}).get("account_id")
                or data.get("account_id")
                or data.get("result", {}).get("sub_account_id")
                or ""
            )
            logger.info(f"[GrvtClient] Login OK - account_id={self.account_id}")
            return True
        except Exception as e:
            logger.error(f"[GrvtClient] Login failed: {e}")
            return False

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        logger.info(f"[GrvtClient] set_leverage({symbol}, {leverage}) - no-op on GRVT")

    async def tick_size(self, symbol: str) -> str:
        try:
            r = await self.client.post(
                "https://market-data.grvt.io/full/v1/instrument",
                json={"instrument": symbol},
                timeout=10,
            )
            ts = r.json().get("result", {}).get("tick_size", "0.1")
            logger.info(f"[GrvtClient] tick_size({symbol}) = {ts}")
            return str(ts)
        except Exception as e:
            logger.warning(f"[GrvtClient] tick_size error: {e}, default=0.1")
            return "0.1"

    async def fetch_mid_price(self, symbol: str) -> float:
        try:
            r = await self.client.post(
                GRVT_MARKET_URL,
                json={"instrument": symbol},
                timeout=10,
            )
            return float(r.json().get("result", {}).get("mark_price", 0))
        except Exception as e:
            logger.warning(f"[GrvtClient] fetch_mid_price error: {e}")
            return 0.0

    def _sign_order(
        self,
        sub_account_id: str,
        client_order_id: int,
        time_in_force_int: int,
        instrument: str,
        size_str: str,
        limit_price_str: str,
        is_buying: bool,
        nonce: int,
        expiration_ns: str,
    ) -> Dict:
        try:
            from eth_account import Account
            acct = Account.from_key(self.private_key)

            domain = {
                "name":    "GRVT Exchange",
                "version": "1",
                "chainId": int(GRVT_CHAIN_ID),
            }
            message_types = {
                "Order": [
                    {"name": "subAccountID",  "type": "uint64"},
                    {"name": "clientOrderID", "type": "uint64"},
                    {"name": "timeInForce",   "type": "uint8"},
                    {"name": "postOnly",      "type": "bool"},
                    {"name": "reduceOnly",    "type": "bool"},
                    {"name": "legs",          "type": "OrderLeg[]"},
                    {"name": "nonce",         "type": "uint32"},
                    {"name": "expiration",    "type": "int64"},
                ],
                "OrderLeg": [
                    {"name": "instrument",     "type": "string"},
                    {"name": "size",           "type": "string"},
                    {"name": "limitPrice",     "type": "string"},
                    {"name": "isBuyingAsset",  "type": "bool"},
                ],
            }
            message_data = {
                "subAccountID":  int(sub_account_id),
                "clientOrderID": client_order_id,
                "timeInForce":   time_in_force_int,
                "postOnly":      False,
                "reduceOnly":    False,
                "legs": [{
                    "instrument":    instrument,
                    "size":          size_str,
                    "limitPrice":    limit_price_str,
                    "isBuyingAsset": is_buying,
                }],
                "nonce":      nonce,
                "expiration": int(expiration_ns),
            }
            signed = acct.sign_typed_data(
                domain_data   = domain,
                message_types = message_types,
                message_data  = message_data,
            )
            return {
                "signer":     acct.address,
                "r":          hex(signed.r),
                "s":          hex(signed.s),
                "v":          signed.v,
                "expiration": expiration_ns,
                "nonce":      nonce,
                "chain_id":   GRVT_CHAIN_ID,
            }
        except Exception as e:
            logger.warning(f"[GrvtClient] EIP-712 signing failed: {e}")
            return {
                "signer":     "0x0000000000000000000000000000000000000000",
                "r":          "0x" + "0" * 64,
                "s":          "0x" + "0" * 64,
                "v":          27,
                "expiration": expiration_ns,
                "nonce":      nonce,
                "chain_id":   GRVT_CHAIN_ID,
            }

    async def _place_single_order(
        self,
        symbol: str,
        is_buying: bool,
        amount: Decimal,
        is_market: bool,
        limit_price: Optional[Decimal],
        time_in_force: str,
        reduce_only: bool = False,
    ) -> Dict:
        if not self.cookie:
            raise RuntimeError("Not authenticated - call login() first")

        tif_map = {
            "GTC":               ("GOOD_TILL_TIME",      1),
            "IOC":               ("IMMEDIATE_OR_CANCEL", 3),
            "FOK":               ("FILL_OR_KILL",        4),
            "GOOD_TILL_TIME":    ("GOOD_TILL_TIME",      1),
            "IMMEDIATE_OR_CANCEL": ("IMMEDIATE_OR_CANCEL", 3),
            "FILL_OR_KILL":      ("FILL_OR_KILL",        4),
        }
        tif_str, tif_int = tif_map.get(time_in_force.upper(), ("IMMEDIATE_OR_CANCEL", 3))
        if is_market:
            tif_str, tif_int = "IMMEDIATE_OR_CANCEL", 3

        lp_str = "0"
        if not is_market and limit_price is not None:
            lp_str = str(limit_price)

        size_str        = str(amount)
        client_order_id = random.randint(2**63, 2**64 - 1)
        nonce           = random.randint(0, 4294967295)
        exp_ns          = str(int((time.time() + 86400 * 29) * 1_000_000_000))

        sig = self._sign_order(
            sub_account_id    = self.account_id,
            client_order_id   = client_order_id,
            time_in_force_int = tif_int,
            instrument        = symbol,
            size_str          = size_str,
            limit_price_str   = lp_str,
            is_buying         = is_buying,
            nonce             = nonce,
            expiration_ns     = exp_ns,
        )

        order_payload = {
            "sub_account_id": self.account_id,
            "is_market":      is_market,
            "time_in_force":  tif_str,
            "post_only":      False,
            "reduce_only":    reduce_only,
            "legs": [{
                "instrument":     symbol,
                "size":           size_str,
                "limit_price":    lp_str,
                "is_buying_asset": is_buying,
            }],
            "signature": sig,
            "metadata": {
                "client_order_id": str(client_order_id),
            },
        }

        headers = {
            "Cookie":       f"gravity={self.cookie}",
            "Content-Type": "application/json",
        }
        body = {"order": order_payload}

        import json
        logger.info(f"[GrvtClient] POST {GRVT_ORDER_URL}")
        logger.debug(f"[GrvtClient] body={json.dumps(body, indent=2)}")

        r = await self.client.post(GRVT_ORDER_URL, json=body, headers=headers)
        logger.info(f"[GrvtClient] response {r.status_code}: {r.text[:400]}")

        if r.status_code not in (200, 201):
            raise RuntimeError(f"GRVT create_order {r.status_code}: {r.text[:400]}")

        result = r.json().get("result", r.json())
        return {
            "order_id":        result.get("order_id", ""),
            "status":          result.get("state", {}).get("status", ""),
            "client_order_id": str(client_order_id),
        }

    async def place_entry_with_tpsl(
        self,
        symbol: str,
        entry_side: str,
        amount: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        time_in_force: str = "GTC",
        reference_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
    ) -> Dict:
        is_market = (order_type.lower() == "market")
        is_buying = (entry_side.lower() == "buy")
        amt = Decimal(str(amount))
        lp  = Decimal(str(limit_price)) if limit_price else None

        entry_result = await self._place_single_order(
            symbol        = symbol,
            is_buying     = is_buying,
            amount        = amt,
            is_market     = is_market,
            limit_price   = lp,
            time_in_force = time_in_force,
        )
        logger.info(f"[GrvtClient] Entry order placed: {entry_result}")

        tp_result = sl_result = None

        if tp_price:
            try:
                tp_result = await self._place_single_order(
                    symbol        = symbol,
                    is_buying     = not is_buying,
                    amount        = amt,
                    is_market     = False,
                    limit_price   = Decimal(str(tp_price)),
                    time_in_force = "GTC",
                    reduce_only   = True,
                )
                logger.info(f"[GrvtClient] TP order placed: {tp_result}")
            except Exception as e:
                logger.warning(f"[GrvtClient] TP placement failed: {e}")

        if sl_price:
            try:
                sl_result = await self._place_single_order(
                    symbol        = symbol,
                    is_buying     = not is_buying,
                    amount        = amt,
                    is_market     = True,
                    limit_price   = None,
                    time_in_force = "IOC",
                    reduce_only   = True,
                )
                logger.info(f"[GrvtClient] SL order placed: {sl_result}")
            except Exception as e:
                logger.warning(f"[GrvtClient] SL placement failed: {e}")

        return {
            "parent_order_id": entry_result.get("order_id", ""),
            "tp_order_id":     tp_result.get("order_id", "") if tp_result else None,
            "sl_order_id":     sl_result.get("order_id", "") if sl_result else None,
            "entry_result":    entry_result,
        }

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
'''

path = "elfa_grvt_bot/grvt_client.py"
with open(path, "w", encoding="utf-8") as f:
    f.write(NEW_CONTENT)
print(f"OK - {path} completely rewritten")

with open(path, encoding="utf-8") as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
print("\n=== Methods ===")
for i, l in enumerate(lines):
    if "    async def " in l or ("    def " in l and "__" not in l):
        print(f"{i+1:03}: {l.rstrip()}")
