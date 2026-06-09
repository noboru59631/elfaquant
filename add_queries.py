import sqlite3, httpx, pathlib, json

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

conn = sqlite3.connect('registry.db')
conn.execute("UPDATE strategies SET status='active' WHERE status='fired'")
print('OK - fired reset')

queries = [
    ('SHORT_MOMENTUM',  'BTC 1H RSI Bear Momentum',  'sell', 'crosses_below', '1h',  50),
    ('LONG_MOMENTUM',   'BTC 1H RSI Bull Momentum',  'buy',  'crosses_above', '1h',  50),
    ('SHORT_15m_ENTRY', 'BTC 15m RSI Short Entry',   'sell', 'crosses_below', '15m', 45),
]

sql = (
    'INSERT INTO strategies ('
    'query_id,title,description,eql_json,symbol,'
    'side,amount,order_type,price,leverage,'
    'time_in_force,reduce_only,max_notional_usd,'
    'tp_pct,sl_pct,env,status,created_at,updated_at) '
    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime("now"),datetime("now"))'
)

for role, title, side, op, tf, val in queries:
    body = {
        'title': title,
        'description': title,
        'query': {
            'conditions': {'AND': [{
                'source': 'ta',
                'method': 'rsi',
                'args': {'sÊbol': 'BTC', 'timeframe': tf, 'period': 14},
                'operator': op,
                'value': val
            }]},
            'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': title}}],
            'expiresIn': '168h'
        }
    }
    r = httpx.post('https://api.elfa.ai/v2/auto/queries', headers=headers, json=body, timeout=15)
    if r.status_code == 201:
        new_id = r.json().get('id', '')
        conn.execute(sql, (
            new_id, role, title, json.dumps(body),
            'BTC_USDT_Perp', side, 0.02, 'market', None, 2,
            'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active'
        ))
        print('OK ' + role + ' -> ' + new_id[:8])
    else:
        print('ERR ' + role + ' ' + str(r.status_code) + ' ' + r.text[:100])

conn.commit()
print('')
print('=== Final DB ===')
for row in conn.execute('SELECT query_id, title, status FROM strategies'):
    print(row)
conn.close()
