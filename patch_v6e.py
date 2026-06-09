with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

old = '''async def place_market_close(grvt: GrvtClient,
                              is_buying: bool, size: Decimal):
    """Place market order to close position."""
    try:
        await grvt._place_single_order(
            symbol=SYMBOL, is_buying=is_buying,
            amount=size, is_market=True,
            time_in_force="IOC",
        )
    except Exception as e:
        print(f"  [market close error] {e}")'''

new = '''async def place_market_close(grvt: GrvtClient,
                              is_buying: bool, size: Decimal,
                              mid: Decimal = Decimal("0")):
    """Place market order to close position.
    limit_price is required by _place_single_order even for market orders.
    Use mid price with 2% slippage buffer as limit_price.
    """
    try:
        # 2% slippage buffer to ensure fill
        if mid == Decimal("0"):
            mid = Decimal("99999") if is_buying else Decimal("1")
        slippage = Decimal("1.02") if is_buying else Decimal("0.98")
        lp = (mid * slippage).quantize(Decimal("0.1"))
        await grvt._place_single_order(
            symbol=SYMBOL, is_buying=is_buying,
            amount=size, is_market=True,
            limit_price=lp,
            time_in_force="IOC",
            reduce_only=True,
        )
    except Exception as e:
        print(f"  [market close error] {e}")'''

content = content.replace(old, new)

with open('mm_bot_v6.py', 'w', encoding='utf-8') as f:
    f.write(content)

if 'slippage buffer' in content:
    print("✅ place_market_close修正完了")
else:
    print("❌ 修正失敗")
