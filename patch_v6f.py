with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

old = '''async def market_close_all(grvt: GrvtClient, reason: str = ""):
    """Flatten entire position with market order."""
    global position, daily_pnl, market_closes, entry_price
    if abs(position) < Decimal("0.001"):
        return
    is_buy = position < 0
    size   = abs(position)
    fee    = size * entry_price * TAKER_FEE
    daily_pnl     -= fee
    market_closes  += 1
    await cancel_all(grvt)
    await place_market_close(grvt, is_buy, size)
    print(f"  🛑 CLOSE [{reason}]"
          f" size={float(size):.3f} fee=-${float(fee):.4f}")
    position    = Decimal("0")
    entry_price = Decimal("0")'''

new = '''async def market_close_all(grvt: GrvtClient, reason: str = "",
                            mid: Decimal = Decimal("0")):
    """Flatten entire position with market order."""
    global position, daily_pnl, market_closes, entry_price
    if abs(position) < Decimal("0.001"):
        return
    is_buy = position < 0
    size   = abs(position)
    fee    = size * entry_price * TAKER_FEE
    daily_pnl     -= fee
    market_closes  += 1
    await cancel_all(grvt)
    await place_market_close(grvt, is_buy, size, mid)
    print(f"  🛑 CLOSE [{reason}]"
          f" size={float(size):.3f} fee=-${float(fee):.4f}")
    position    = Decimal("0")
    entry_price = Decimal("0")'''

content = content.replace(old, new)

with open('mm_bot_v6.py', 'w', encoding='utf-8') as f:
    f.write(content)

if 'mid: Decimal = Decimal("0")' in content:
    print("✅ market_close_all修正完了")
else:
    print("❌ 修正失敗")
