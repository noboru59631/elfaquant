import sqlite3, httpx, pathlib
from datetime import datetime

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

OLD_IDS = [
    '91292be5-e977-40ba-a531-6e1c7ef7de11',
    'e3dc7745-77c1-4dd2-bf28-b861e85f14f2',
    '67f8b334-633e-4c7d-9694-bb380c783940',
]

NEW_QUERIES = [
    {
        'db_title': 'BEAR_RSI_CROSS_35',
        'side': 'sell',
        'body': {
            'title': 'BTC 1H RSI crosses below 35 v2',
            'description': 'BTC 1H RSI crosses below 35',
            'query': {
                'conditions': {'AND': [{
                    'source': 'ta', 'method': 'rsi',
                    'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14},
                    'operator': 'crosses_below', 'value': 35
                }]},
                'actions': [{'stepId': 'step_1', 'type': 'notify',
                             'params': {'message': 'BTC 1H RSI crosses below 35'}}],
                'expiresIn': '168h'
            }
        }
    },
    {
        'db_title': 'BEAR_FILTER_SHORT_V2',
        'side': 'sell',
        'body': {
            'title': 'BTC 4H RSI crosses below 40 v2',
            'description': 'BTC 4H RSI crosses below 40',
            'query': {
                'conditions': {'AND': [{
                    'source': 'ta', 'method': 'rsi',
                    'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14},
                    'operator': 'crosses_below', 'value': 40
                }]},
                'actions': [{'stepId': 'step_1', 'type': 'notify',
                             'params': {'message': 'BTC 4H RSI crosses below 40'}}],
                'expiresIn': '168h'
            }
        }
    },
    {
        'db_title': 'SHORT_REVERSAL_V2',
        'side': 'sell',
        'body': {
            'title': 'BTC 4H RSI crosses below 45 v2',
            'description': 'BTC 4H RSI crosses below 45',
            'query': {
                'conditions': {'AND': [{
                    'source': 'ta', 'method': 'rsi',
                    'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14},
                    'operator': 'crosses_below', 'value': 45
                }]},
                'actions': [{'stepId': 'step_1', 'type': 'notify',
                             'params': {'message': 'BTC 4H RSI crosses below 45'}}],
                'expiresIn': '168h'
            }
        }
    },
]

c = sqlite3.connect('registry.db')
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

for old_id in OLD_IDS:
    c.execute('DELETE FROM strategies WHERE query_id=?', (old_id,))
    print('Deleted:', old_id[:8], '- rows:', c.execute('SELECT changes()').fetchone()[0])
c.commit()

for q in NEW_QUERIES:
    r = httpx.post('https://api.elfa.ai/v2/auto/queries',
                   headers=headers, json=q['body'], timeout=15)
    print('POST', q['db_title'], ':', r.status_code)
    if r.status_code == 201:
        new_id = r.json().get('id', '')
        wo = r.json().get('latestEvaluation', {}).get('wouldTriggerNow', 'unknown')
        print('  ID:', new_id)
        print('  wouldTriggerNow:', wo)
        row = (new_id, q['db_title'], q['body']['description'], '{}',
               'BTC_USDT_Perp', q['side'], 0.02, 'market', None, 2,
               'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
        c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
        c.commit()
        print('  OK inserted', q['db_title'])
    else:
        print('  ERROR:', r.text[:200])

print()
print('=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
