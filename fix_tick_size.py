# ---- Step1: core.py line 234付近を確認 ----
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

print('=== core.py lines 228-245 (process_fire tick_size付近) ===')
for i in range(227, 245):
    print(f'{i+1:03}: {lines[i].rstrip()}')

# ---- Step2: grvt_client.py に tick_size メソッドを追加 ----
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    gc = f.read()

if 'async def tick_size' not in gc:
    stub = '''
    async def tick_size(self, symbol: str) -> str:
        """Fetch tick_size for the given instrument from GRVT market data API."""
        import logging as _lg
        url = "https://market-data.grvt.io/full/v1/instrument"
        try:
            r = await self._client.post(url, json={"instrument": symbol}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                result = data.get("result", data)
                ts = result.get("tick_size", "0.1")
                _lg.getLogger(__name__).info(
                    f"[GrvtClient] tick_size({symbol}) = {ts}")
                return ts
        except Exception as e:
            _lg.getLogger(__name__).warning(
                f"[GrvtClient] tick_size fetch failed: {e}, using default 0.1")
        return "0.1"

'''
    # fetch_mid_priceの直前に挿入
    target = '    async def fetch_mid_price'
    if target in gc:
        gc = gc.replace(target, stub + '    async def fetch_mid_price')
        with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
            f.write(gc)
        print('\nOK - tick_size method added to grvt_client.py')
    else:
        print('\nERROR: fetch_mid_price not found in grvt_client.py')
else:
    print('\nOK - tick_size already exists')

# ---- Step3: grvt_client.py の _client 属性を確認 ----
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    gc_lines = f.readlines()

print('\n=== grvt_client.py __init__ (lines 13-20) ===')
for i in range(12, 22):
    if i < len(gc_lines):
        print(f'{i+1:03}: {gc_lines[i].rstrip()}')

# ---- Step4: 943c7cbd を fired にして renew対象に ----
import sqlite3
c = sqlite3.connect('registry.db')
c.execute("UPDATE strategies SET status='fired' WHERE query_id='943c7cbd-ba20-40f1-9bc6-343396ae251b'")
c.commit()
print('\nOK - 943c7cbd set to fired')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
