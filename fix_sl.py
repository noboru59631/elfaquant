with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    content = f.read()

old = '''        if sl_price:
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
                logger.warning(f"[GrvtClient] TP placement failed: {e}")'''

new = '''        if sl_price:
            try:
                # SLはlimit注文で送信しない（即時約定するため）
                # GRVTのWebUIでstop注文として設定すること
                logger.info(f"[GrvtClient] SL skipped (use WebUI stop order) sl_price={sl_price}")
            except Exception as e:
                logger.warning(f"[GrvtClient] SL placement failed: {e}")'''

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK - SL fixed (disabled market SL)")
else:
    print("ERROR: pattern not found")
