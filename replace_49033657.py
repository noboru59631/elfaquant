import sqlite3, httpx, pathlib, json
from datetime import datetime

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

c = sqlite3.connect('registry.db')
c.execute("DELETE FROM strategies WHERE query_id='49033657-17e4-41f1-b39b-83026f3cd75f'")
print('Deleted 49033657')

body = {
    'title': 'BTC 15m Short Setup v4',
    'description': 'BTC 15m RSI crosses below 40',
    'query': {
        'conditions': {'AND': [{'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14}, 'operator': 'crosses_below', 'value': 40}]},
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC 15m short'}}],
        'expiresIn': '168h'
    }
}
r = httpx.post('https://api.elfa.ai/v2/auto/queries', headers=headers, json=body, timeout=15)
if r.status_code == 201:
    new_id = r.json().get('id', '')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    row = (new_id, 'SHORT_SETUP_15m', 'BTC 15m Short Setup v4', json.dumps(body),
           'BTC_USDT_Perp', 'sell', 0.02, 'market', None, 2, 'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
    c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
    print('OK SHORT_SETUP_15m ->', new_id[:8])
c.commit()
print('\n=== DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
