with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

# 323-336行目をSL trigger注文に置き換え
new_sl = '''        if sl_price:
            try:
                # SL: trigger付きlimit注文 (STOP_LOSS)
                sl_limit = sl_price * 1.005 if not is_buying else sl_price * 0.995
                payload = {
                    "order": {
                        "sub_account_id": self.account_id,
                        "is_market":      False,
                        "time_in_force":  "GOOD_TILL_TIME",
                        "post_only":      False,
                        "reduce_only":    True,
                        "legs": [{
                            "instrument":      symbol,
                            "size":            str(amt),
                            "limit_price":     str(round(sl_limit, 1)),
                            "is_buying_asset": not is_buying,
                        }],
                        "signature": self._sign_order(
                            symbol=symbol, size=amt,
                            limit_price=Decimal(str(round(sl_limit, 1))),
                            is_buying=not is_buying,
                        ),
                        "metadata": {"client_order_id": str(random.getrandbits(64))},
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
                r = await self._client.post(
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

'''

# 323行目(index 322)から336行目(index 335)を置き換え
lines[322:336] = new_sl.splitlines(keepends=True)

with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"OK - SL trigger order implemented ({len(lines)} lines)")
