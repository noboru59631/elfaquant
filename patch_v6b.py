with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

old = '''def adjust_risk(pnl: Decimal) -> None:
    """
    Auto-adjust risk_mult every RISK_ADJUST_SEC.
    PnL > 0 -> risk_mult -= 0.05 (floor 0.8)
    PnL < 0 -> risk_mult += 0.10 (ceil  2.0)
    """
    global risk_mult
    if pnl > 0:
        risk_mult = max(Decimal("0.8"),
                        risk_mult - Decimal("0.05"))
    else:
        risk_mult = min(Decimal("2.0"),
                        risk_mult + Decimal("0.1"))'''

new = '''def adjust_risk(pnl: Decimal) -> None:
    """
    Auto-adjust risk_mult every RISK_ADJUST_SEC.
    PnL > 0  -> risk_mult -= 0.05 (floor 0.8)
    PnL < 0  -> risk_mult += 0.10 (ceil  2.0)
    PnL == 0 -> no change (waiting for first fill)
    """
    global risk_mult
    if pnl > 0:
        risk_mult = max(Decimal("0.8"),
                        risk_mult - Decimal("0.05"))
    elif pnl < 0:
        risk_mult = min(Decimal("2.0"),
                        risk_mult + Decimal("0.1"))
    # pnl == 0: no adjustment yet'''

content = content.replace(old, new)

with open('mm_bot_v6.py', 'w', encoding='utf-8') as f:
    f.write(content)

if 'pnl == 0: no adjustment' in content:
    print("✅ risk_mult修正完了")
else:
    print("❌ 修正失敗")
