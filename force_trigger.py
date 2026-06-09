"""force_trigger.py - wouldTriggerNow=True のクエリを強制的に処理"""
import asyncio, pathlib, httpx, sqlite3, json, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

# wouldTriggerNow=True のクエリを全件チェック
headers = {'x-elfa-api-key': env.get('ELFA_API_KEY', '')}
conn = sqlite3.connect('registry.db')
rows = conn.execute(
    "SELECT query_id, title, side, symbol, amount, order_type, leverage "
    "FROM strategies WHERE status='active'"
).fetchall()

trigger_targets = []
for query_id, title, side, symbol, amount, order_type, leverage in rows:
    r = httpx.get(
        f'https://api.elfa.ai/v2/auto/queries/{query_id}',
        headers=headers, timeout=10
    )
    d = r.json()
    wtn = d.get('latestEvaluation', {}).get('wouldTriggerNow', False)
    status = d.get('status', '')
    print(f'{title[:30]:<30} status={status:<10} wouldTriggerNow={wtn}')
    if wtn:
        trigger_targets.append((query_id, title, side, symbol, amount, order_type, leverage))

print(f'\n=== 発火対象: {len(trigger_targets)} 件 ===')
for t in trigger_targets:
    print(f'  {t[1]} ({t[0][:8]}...) side={t[2]} amount={t[3]}')

if not trigger_targets:
    print('発火対象なし')
    conn.close()
    exit()

# 発火対象を注文送信
async def fire_orders():
    from elfa_grvt_bot.grvt_client import GrvtClient
    grvt = GrvtClient(
        env.get('GRVT_TRADING_API_KEY', ''),
        env.get('GRVT_TRADING_PRIVATE_KEY', '')
    )
    try:
        ok = await grvt.login()
        if not ok:
            print('ERROR: Login failed')
            return
        print(f'Login OK: account_id={grvt.account_id}')

        price = await grvt.fetch_mid_price('BTC_USDT_Perp')
        print(f'BTC price: {price}')

        for query_id, title, side, symbol, amount, order_type, leverage in trigger_targets:
            print(f'\n--- Firing {title} ---')
            print(f'    {side.upper()} {amount} {symbol} ({order_type})')
            try:
                result = await grvt.place_entry_with_tpsl(
                    symbol          = symbol,
                    entry_side      = side,
                    amount          = float(amount),
                    order_type      = order_type,
                    reference_price = price,
                )
                print(f'    SUCCESS: order_id={result.get("parent_order_id")} status={result.get("entry_result", {}).get("status")}')
                # DBを更新
                from datetime import datetime
                now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
                conn.execute(
                    "INSERT OR IGNORE INTO fires "
                    "(event_id, query_id, raw_payload, outcome, received_at, placed_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (f'force_{query_id[:8]}', query_id, '{}', 'placed', now, now)
                )
                conn.execute(
                    "UPDATE strategies SET status='fired' WHERE query_id=?",
                    (query_id,)
                )
                conn.commit()
                print(f'    DB updated: status=fired')
            except Exception as e:
                print(f'    ERROR: {e}')
    finally:
        await grvt.close()

asyncio.run(fire_orders())
conn.close()
print('\nDone.')
