import sqlite3, httpx, pathlib, json
from datetime import datetime

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

queries = [
    (
        'BEAR_EMA200_4H',
        'BTC Price Below 4H EMA200',
        {'conditions': {'AND': [{'source': 'price', 'method': 'current', 'args': {'symbol': 'BTC'}, 'operator': '<', 'value': {'source': 'ta', 'method': 'ema', 'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 200}}}]},
         'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC below 4H EMA200'}}],
         'expiresIn': '168h'},
        'sell'
    ),
    (
        'BEAR_EMA50_1H',
        'BTC Price Below 1H EMA50',
        {'conditions': {'AND': [{'source': 'price', 'method': 'current', 'args': {'symbol': 'BTC'}, 'operator': '<', 'value': {'source': 'ta', 'method': 'ema', 'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 50}}}]},
         'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC below 1H EMA50'}}],
         'expiresIn': '168h'},
        'sell'
    ),
    (
        'BEAR_MOMENTUM_4H',
        'BTC 4H RSI Below 50',
        {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14}, 'operator': '<', 'value': 50}]},
         'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC 4H RSI below 50'}}],
         'expiresIn': '168h'},
        'sell'
    ),
]

c = sqlite3.connect('registry.db')
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
added = 0

for role, title, qbody, side in queries:
    payload = {'title': title, 'description': title, 'query': qbody}
    r = httpx.post('https://api.elfa.ai/v2/auto/queries', headers=headers, json=payload, timeout=15)
    if r.status_code == 201:
        d = r.json()
        new_id = d.get('id', '')
        ev = d.get('latestEvaluation', {}) or {}
        wo = ev.get('wouldTriggerNow', 'unknown')
        row = (new_id, role, title, json.dumps(qbody), 'BTC_USDT_Perp', side,
               0.02, 'market', None, 2, 'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
        c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
        print('OK ' + role + ' -> ' + new_id[:8] + ' wouldTrigger=' + str(wo))
        added += 1
    else:
        print('ERR ' + role + ' ' + str(r.status_code) + ' ' + r.text[:100])

c.commit()
print('')
print('Added:', added)
print('')
print('=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
