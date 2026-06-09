import sqlite3, httpx, pathlib
from datetime import datetime

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

c = sqlite3.connect('registry.db')
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

# fired状態のクエリを取得
fired = list(c.execute("SELECT query_id, title FROM strategies WHERE status='fired'"))
print(f'Fired strategies: {len(fired)}')
for qid, title in fired:
    print(f'  {qid[:8]} {title}')

# 各firedクエリを新規作成して置き換え
REPLACE_MAP = {
    'BEAR_RSI_CROSS_35': {
        'title': 'BTC 1H RSI crosses below 35 v3',
        'description': 'BTC 1H RSI crosses below 35',
        'query': {
            'conditions': {'AND': [{
                'source': 'ta', 'method': 'rsi',
                'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14},
                'operator': 'crosses_below', 'value': 35
            }]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 1H RSI crosses below 35 v3'}}],
            'expiresIn': '168h'
        }
    },
    'SHORT_SETUP_15m': {
        'title': 'BTC 15m RSI crosses below 42 v3',
        'description': 'BTC 15m RSI crosses below 42',
        'query': {
            'conditions': {'AND': [{
                'source': 'ta', 'method': 'rsi',
                'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14},
                'operator': 'crosses_below', 'value': 42
            }]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 15m RSI crosses below 42 v3'}}],
            'expiresIn': '168h'
        }
    },
}

replaced = 0
for qid, title in fired:
    if title not in REPLACE_MAP:
        print(f'  SKIP {title} (no replacement defined)')
        continue

    body = REPLACE_MAP[title]
    r = httpx.post('https://api.elfa.ai/v2/auto/queries',
                   headers=headers, json=body, timeout=15)
    if r.status_code == 201:
        new_id = r.json().get('id', '')
        c.execute('DELETE FROM strategies WHERE query_id=?', (qid,))
        row = (new_id, title, body['description'], '{}',
               'BTC_USDT_Perp', 'sell', 0.02, 'market', None, 2,
               'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
        c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
        c.commit()
        print(f'  OK {title}: {qid[:8]} -> {new_id[:8]}')
        replaced += 1
    else:
        print(f'  ERROR {title}: {r.status_code} {r.text[:100]}')

print(f'Replaced: {replaced}')
print()
print('=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
