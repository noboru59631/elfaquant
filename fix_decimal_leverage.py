with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# ---- Fix 1: Decimal * float TypeError ----
# compute_target_priceでDecimalをfloatに変換
old1 = "if kind == 'tp': return reference * (1 - pct_frac)"
new1 = "if kind == 'tp': return float(reference) * (1 - pct_frac)"
if old1 in content:
    content = content.replace(old1, new1)
    print('OK - Fix1: Decimal*float fixed (tp)')
else:
    print('WARN - Fix1 pattern not found (tp)')

old2 = "if kind == 'sl': return reference * (1 + pct_frac)"
new2 = "if kind == 'sl': return float(reference) * (1 + pct_frac)"
if old2 in content:
    content = content.replace(old2, new2)
    print('OK - Fix1: Decimal*float fixed (sl)')
else:
    print('WARN - Fix1 pattern not found (sl) - checking alternatives')

# compute_target_price内の全パターンを念のためカバー
import re
content = re.sub(
    r'return\s+reference\s+\*\s+\(1\s*[-+]',
    'return float(reference) * (1 -' if '-' in old1 else 'return float(reference) * (1 +',
    content
)

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.write(content)

# ---- Fix 2: set_leverage missing ----
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    gc = f.read()

if 'def set_leverage' not in gc:
    stub = '''
    async def set_leverage(self, symbol: str, leverage: int) -> None:
        """Stub: GRVT leverage is set per-order, not account-wide."""
        import logging as _lg
        _lg.getLogger(__name__).info(
            f'[GrvtClient] set_leverage({symbol}, {leverage}) - no-op on GRVT')
        return
'''
    # クラスの最後のメソッドの直前に挿入（classの末尾に追加）
    # fetch_mid_priceの後に追加
    target = '    async def fetch_mid_price'
    if target in gc:
        gc = gc.replace(target, stub + '\n    async def fetch_mid_price')
        with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
            f.write(gc)
        print('OK - Fix2: set_leverage stub added to grvt_client.py')
    else:
        print('WARN - Fix2: fetch_mid_price not found, appending to end')
        with open('elfa_grvt_bot/grvt_client.py', 'a', encoding='utf-8') as f:
            f.write(stub)
        print('OK - Fix2: set_leverage stub appended')
else:
    print('OK - Fix2: set_leverage already exists')

# ---- Verify core.py lines 380-390 ----
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== core.py lines 378-392 (compute_target_price) ===')
for i in range(377, min(len(lines), 393)):
    print(f'{i+1:03}: {lines[i].rstrip()}')
