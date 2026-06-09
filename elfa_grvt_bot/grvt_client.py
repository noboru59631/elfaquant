"""
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
            # レスポンス構造: {"status":"success","sub_account_id":"7643292000705847",...}
            self.account_id = str(
                data.get("sub_account_id")
                or data.get("account_id")
                or data.get("result", {}).get("sub_account_id")
                or data.get("result", {}).get("account_id")
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
        is_market: bool,
        post_only: bool = False,
        reduce_only: bool = False,
    ) -> Dict:
        """
        EIP-712 sign using official GRVT pysdk schema.
        Ref: github.com/gravity-technologies/grvt-pysdk/blob/main/src/pysdk/grvt_raw_signing.py
        """
        from eth_account import Account
        from eth_account.messages import encode_typed_data
        from decimal import Decimal as _Dec

        # --- instrument metadata (hardcoded for BTC_USDT_Perp; extend as needed) ---
        INSTRUMENT_META = {
            "BTC_USDT_Perp":  {"hash": 0x030501,  "base_decimals": 9},
            "ETH_USDT_Perp":  {"hash": 0x030502,  "base_decimals": 9},
            "SOL_USDT_Perp":  {"hash": 0x030503,  "base_decimals": 9},
        }
        meta = INSTRUMENT_META.get(instrument, {"hash": 0x030501, "base_decimals": 9})
        asset_id      = meta["hash"]
        size_mult     = 10 ** meta["base_decimals"]   # 1_000_000_000
        PRICE_MULT    = 1_000_000_000

        size_int       = int(_Dec(size_str)        * _Dec(size_mult))
        limit_price_int= int(_Dec(limit_price_str) * _Dec(PRICE_MULT))

        # --- EIP-712 domain  (version MUST be "0") ---
        domain = {
            "name":    "GRVT Exchange",
            "version": "0",
            "chainId": 325,          # PROD chain ID
        }

        # --- message types (from official SDK grvt_raw_signing.py) ---
        message_types = {
            "Order": [
                {"name": "subAccountID",  "type": "uint64"},
                {"name": "isMarket",      "type": "bool"},
                {"name": "timeInForce",   "type": "uint8"},
                {"name": "postOnly",      "type": "bool"},
                {"name": "reduceOnly",    "type": "bool"},
                {"name": "legs",          "type": "OrderLeg[]"},
                {"name": "nonce",         "type": "uint32"},
                {"name": "expiration",    "type": "int64"},
            ],
            "OrderLeg": [
                {"name": "assetID",          "type": "uint256"},
                {"name": "contractSize",     "type": "uint64"},
                {"name": "limitPrice",       "type": "uint64"},
                {"name": "isBuyingContract", "type": "bool"},
            ],
        }

        # --- message data ---
        message_data = {
            "subAccountID":  int(sub_account_id),
            "isMarket":      is_market,
            "timeInForce":   time_in_force_int,
            "postOnly":      post_only,
            "reduceOnly":    reduce_only,
            "legs": [{
                "assetID":          asset_id,
                "contractSize":     size_int,
                "limitPrice":       limit_price_int,
                "isBuyingContract": is_buying,
            }],
            "nonce":      nonce,
            "expiration": int(expiration_ns),
        }

        try:
            acct           = Account.from_key(self.private_key)
            signable       = encode_typed_data(domain, message_types, message_data)
            signed         = Account.sign_message(signable, self.private_key)
            r_hex = "0x" + signed.r.to_bytes(32, byteorder="big").hex()
            s_hex = "0x" + signed.s.to_bytes(32, byteorder="big").hex()
            logger.info(f"[GrvtClient] EIP-712 signed OK signer={acct.address}")
            return {
                "signer":     acct.address,
                "r":          r_hex,
                "s":          s_hex,
                "v":          signed.v,
                "expiration": expiration_ns,
                "nonce":      nonce,
                "chain_id":   "325",
            }
        except Exception as e:
            logger.error(f"[GrvtClient] EIP-712 signing FAILED: {e}")
            raise

    async def _place_single_order(
        self,
        symbol: str,
        is_buying: bool,
        amount: Decimal,
        is_market: bool,
        limit_price: Optional[Decimal],
        time_in_force: str,
        reduce_only: bool = False,
        post_only: bool = False,
    ) -> Dict:
        if not self.cookie:
            raise RuntimeError("Not authenticated - call login() first")

        tif_map = {
            "GTT":               ("GOOD_TILL_TIME",      1),
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
            is_market         = is_market,
            reduce_only       = reduce_only,
            post_only       = post_only,
        )

        order_payload = {
            "sub_account_id": self.account_id,
            "is_market":      is_market,
            "time_in_force":  tif_str,
            "post_only":      post_only,
            "reduce_only":    reduce_only,
            "legs": [{
                "instrument":      symbol,
                "size":            size_str,
                "limit_price":     lp_str,
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

        import json as _json
        logger.info(f"[GrvtClient] POST {GRVT_ORDER_URL}")
        logger.debug(f"[GrvtClient] body=\n{_json.dumps(body, indent=2)}")

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
                # SL: trigger付きlimit注文 (STOP_LOSS)
                sl_limit = sl_price * 1.005 if not is_buying else sl_price * 0.995
                sl_limit_str    = str(round(sl_limit, 1))
                sl_size_str     = str(amt)
                sl_client_order_id = random.randint(2**63, 2**64 - 1)
                sl_nonce        = random.randint(0, 4294967295)
                sl_exp_ns       = str(int((time.time() + 86400 * 29) * 1_000_000_000))

                sl_sig = self._sign_order(
                    sub_account_id    = self.account_id,
                    client_order_id   = sl_client_order_id,
                    time_in_force_int = 1,  # GOOD_TILL_TIME
                    instrument        = symbol,
                    size_str          = sl_size_str,
                    limit_price_str   = sl_limit_str,
                    is_buying         = not is_buying,
                    nonce             = sl_nonce,
                    expiration_ns     = sl_exp_ns,
                    is_market         = False,
                    post_only         = False,
                    reduce_only       = True,
                )

                payload = {
                    "order": {
                        "sub_account_id": self.account_id,
                        "is_market":      False,
                        "time_in_force":  "GOOD_TILL_TIME",
                        "post_only":      False,
                        "reduce_only":    True,
                        "legs": [{
                            "instrument":      symbol,
                            "size":            sl_size_str,
                            "limit_price":     sl_limit_str,
                            "is_buying_asset": not is_buying,
                        }],
                        "signature": sl_sig,
                        "metadata": {"client_order_id": str(sl_client_order_id)},
                        "trigger": {
                            "trigger_type": "STOP_LOSS",
                            "tpsl": {
                                "trigger_by":    "MARK",
                                "trigger_price": str(round(sl_price, 1)),
                                "close_position": False,
                            }
                        }
                    }
                }
                r = await self.client.post(
                    GRVT_ORDER_URL, json=payload,
                    cookies={"gravity": self.cookie},
                    headers={"Content-Type": "application/json"},
                )
                if r.status_code == 200:
                    sl_result = r.json().get("result", {})
                    logger.info(f"[GrvtClient] SL trigger order placed: {sl_result}")
                else:
                    logger.warning(f"[GrvtClient] SL trigger failed {r.status_code}: {r.text[:200]}")
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
