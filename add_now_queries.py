import sqlite3, httpx, pathlib
from datetime import datetime

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

QUERIES = [
    {
        'db_title': 'SHORT_NOW_1H',
        'body': {
            'title': 'BTC 1H RSI below 29',
            'description': 'BTC 1H RSI below 29',
            'query': {
                'conditions': {'AND': [{
                    'source': 'ta', 'method': 'rsi',
                    'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14},
                    'operator': '<', 'value': 29
                }]},
                'actions': [{'stepId': 'step_1', 'type': 'notify',
                             'params': {'message': 'BTC 1H RSI below 29'}}],
                'expiresIn': '48h'
            }
        }
    },
    {
        'db_title': 'SHORT_NOW_4H',
        'body': {
            'title': 'BTC 4H RSI below 31',
            'description': 'BTC 4H RSI below 31',
            'query': {
                'conditions': {'AND': [{
                    'source': 'ta', 'method': 'rsi',
                    'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14},
                    'operator': '<', 'value': 31
                }]},
                'actions': [{'stepId': 'step_1', 'type': 'notify',
                             'params': {'message': 'BTC 4H RSI below 31'}}],
                'expiresIn': '48h'
            }
        }
    },
]

c = sqlite3.connect('registry.db')
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

for q in QUERIES:
    r = httpx.post('https://api.elfa.ai/v2/auto/queries',
                   headers=headers, json=q['body'], timeout=15)
    print(f"POST {q['db_title']}: {r.status_code}")
    if r.status_code == 201:
        d = r.json()
        new_id = d.get('id', '')
        wtn = d.get('latestEvaluation', {}).get('wouldTriggerNow', 'unknown')
        print(f"  ID: {new_id}")
        print(f"  wouldTriggerNow: {wtn}")
        row = (new_id, q['db_title'], q['body']['description'], '{}',
               'BTC_USDT_Perp', 'sell', 0.02, 'market', None, 2,
               'GTC', 0, 2000.0, 3.5, 1.0, 'prod', 'active', now, now)
        c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
        c.commit()
        print(f"  OK - {q['db_title']} inserted")
    else:
        print(f"  ERROR: {r.text[:200]}")

print('\n=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
