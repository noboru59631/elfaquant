"""
fix_signing.py
公式GRVT pysdk の署名スキーマに完全準拠した _sign_order を修正
"""

NEW_SIGN_METHOD = '''    def _sign_order(
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
'''

# --- _place_single_orderのシグネチャ変更に合わせてis_market引数を追加 ---
NEW_PLACE_SINGLE = '''    async def _place_single_order(
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
            is_market         = is_market,
            reduce_only       = reduce_only,
        )

        order_payload = {
            "sub_account_id": self.account_id,
            "is_market":      is_market,
            "time_in_force":  tif_str,
            "post_only":      False,
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
        logger.debug(f"[GrvtClient] body=\\n{_json.dumps(body, indent=2)}")

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
'''

import re

with open("elfa_grvt_bot/grvt_client.py", encoding="utf-8") as f:
    content = f.read()

# --- _sign_order を置換 ---
sign_pattern = re.compile(
    r'    def _sign_order\(.*?(?=\n    async def |\n    def )',
    re.DOTALL
)
m = sign_pattern.search(content)
if m:
    content = content[:m.start()] + NEW_SIGN_METHOD + content[m.end():]
    print("OK - _sign_order replaced")
else:
    print("ERROR: _sign_order pattern not found")

# --- _place_single_order を置換 ---
place_pattern = re.compile(
    r'    async def _place_single_order\(.*?(?=\n    async def place_entry_with_tpsl)',
    re.DOTALL
)
m2 = place_pattern.search(content)
if m2:
    content = content[:m2.start()] + NEW_PLACE_SINGLE + content[m2.end():]
    print("OK - _place_single_order replaced")
else:
    print("ERROR: _place_single_order pattern not found")

with open("elfa_grvt_bot/grvt_client.py", "w", encoding="utf-8") as f:
    f.write(content)

# 確認
with open("elfa_grvt_bot/grvt_client.py", encoding="utf-8") as f:
    lines = f.readlines()
print(f"\nTotal lines: {len(lines)}")
print("\n=== _sign_order (最初の30行) ===")
for i, l in enumerate(lines):
    if "def _sign_order" in l:
        start = i
        for j in range(start, min(start+35, len(lines))):
            print(f"{j+1:03}: {lines[j].rstrip()}")
        break
