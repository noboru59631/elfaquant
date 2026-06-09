with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    content = f.read()

old = '''    async def _build_order(
        self,
        symbol: str,
        side: str,
        amount: Decimal,
        order_type: str,
        limit_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False
    ) -> Dict:
        """
        Build and sign an order payload
        """
        # This would normally use GRVT's signing SDK
        # Simplified for this example
        order = {
            "sub_account_id": self.account_id,
            "instrument": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(amount),
            "time_in_force": time_in_force,
            "reduce_only": reduce_only,
            "metadata": {
                "client_order_id": self._generate_client_order_id()
            }
        }

        if limit_price is not None:
            order["price"] = str(limit_price)

        return order'''

new = '''    async def _build_order(
        self,
        symbol: str,
        side: str,
        amount: Decimal,
        order_type: str,
        limit_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False
    ) -> Dict:
        """
        Build and sign an order payload using EIP-712 for GRVT ZKSync Hyperchain
        """
        import time, random
        from eth_account import Account
        from eth_account.messages import encode_typed_data

        is_market = (order_type.upper() == "MARKET")
        is_buying = (side.lower() == "buy")

        # time_in_force mapping
        tif_map = {
            "GTC": "GOOD_TILL_TIME",
            "IOC": "IMMEDIATE_OR_CANCEL",
            "FOK": "FILL_OR_KILL",
            "GOOD_TILL_TIME": "GOOD_TILL_TIME",
            "IMMEDIATE_OR_CANCEL": "IMMEDIATE_OR_CANCEL",
        }
        tif = tif_map.get(time_in_force.upper(), "IMMEDIATE_OR_CANCEL")
        # Market orders must be IOC
        if is_market:
            tif = "IMMEDIATE_OR_CANCEL"

        client_order_id = str(random.randint(2**63, 2**64 - 1))
        nonce = random.randint(0, 4294967295)
        expiration_ns = str(int((time.time() + 86400 * 29) * 1_000_000_000))
        chain_id = "325"

        limit_price_str = "0"
        if not is_market and limit_price is not None:
            limit_price_str = str(int(Decimal(str(limit_price)) * Decimal("1000000000")))

        # EIP-712 typed data for GRVT
        typed_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "Order": [
                    {"name": "subAccountID", "type": "uint64"},
                    {"name": "clientOrderID", "type": "uint64"},
                    {"name": "timeInForce", "type": "uint8"},
                    {"name": "postOnly", "type": "bool"},
                    {"name": "reduceOnly", "type": "bool"},
                    {"name": "legs", "type": "OrderLeg[]"},
                ],
                "OrderLeg": [
                    {"name": "instrument", "type": "uint32"},
                    {"name": "size", "type": "uint64"},
                    {"name": "limitPrice", "type": "uint64"},
                    {"name": "isBuyingAsset", "type": "bool"},
                ],
            },
            "domain": {
                "name": "GRVT Exchange",
                "version": "1",
                "chainId": int(chain_id),
            },
            "primaryType": "Order",
            "message": {
                "subAccountID": int(self.account_id),
                "clientOrderID": int(client_order_id),
                "timeInForce": {"GOOD_TILL_TIME": 1, "IMMEDIATE_OR_CANCEL": 3, "FILL_OR_KILL": 4}.get(tif, 3),
                "postOnly": False,
                "reduceOnly": reduce_only,
                "legs": [{
                    "instrument": 0,
                    "size": int(Decimal(str(amount)) * Decimal("1000000000")),
                    "limitPrice": int(limit_price_str) if limit_price_str != "0" else 0,
                    "isBuyingAsset": is_buying,
                }],
            },
        }

        try:
            account = Account.from_key(self.private_key)
            signed = account.sign_typed_data(
                domain_data=typed_data["domain"],
                message_types={k: v for k, v in typed_data["types"].items() if k != "EIP712Domain"},
                message_data=typed_data["message"]
            )
            sig_r = hex(signed.r)
            sig_s = hex(signed.s)
            sig_v = signed.v
            signer = account.address
        except Exception as e:
            import logging as _lg
            _lg.getLogger(__name__).warning(f"[GrvtClient] EIP-712 signing failed: {e}, using dummy sig")
            sig_r = "0x" + "0" * 64
            sig_s = "0x" + "0" * 64
            sig_v = 27
            signer = "0x0000000000000000000000000000000000000000"

        order = {
            "sub_account_id": self.account_id,
            "is_market": is_market,
            "time_in_force": tif,
            "post_only": False,
            "reduce_only": reduce_only,
            "legs": [{
                "instrument": symbol,
                "size": str(amount),
                "limit_price": limit_price_str,
                "is_buying_asset": is_buying,
            }],
            "signature": {
                "signer": signer,
                "r": sig_r,
                "s": sig_s,
                "v": sig_v,
                "expiration": expiration_ns,
                "nonce": nonce,
                "chain_id": chain_id,
            },
            "metadata": {
                "client_order_id": client_order_id,
            }
        }
        return order'''

if old in content:
    content = content.replace(old, new)
    # private_key を __init__ に保存
    if 'self.private_key' not in content:
        content = content.replace(
            '        self.api_key = api_key\n        self.private_key = private_key',
            '        self.api_key = api_key\n        self.private_key = private_key'
        )
        # __init__ の private_key 保存を確認
        if 'self.private_key = private_key' not in content:
            content = content.replace(
                '        self.api_key = api_key',
                '        self.api_key = api_key\n        self.private_key = private_key'
            )
    with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - _build_order replaced with EIP-712 signing')
else:
    print('ERROR: pattern not found')

# 確認
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()
print(f'\n合計行数: {len(lines)}')
print('\n=== __init__ ===')
for i in range(12, 20):
    print(f'{i+1:03}: {lines[i].rstrip()}')
