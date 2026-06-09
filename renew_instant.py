import sqlite3, httpx, pathlib
from datetime import datetime

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}
body = {
    'title': 'BTC 1H RSI below 26 v2',
    'description': 'BTC 1H RSI below 26',
    'query': {
        'conditions': {'AND': [{
            'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14},
            'operator': '<', 'value': 26
        }]},
        'actions': [{'stepId': 'step_1', 'type': 'notify',
                     'params': {'message': 'BTC 1H RSI below 26'}}],
        'expiresIn': '168h'
    }
}

r = httpx.post('https://api.elfa.ai/v2/auto/queries',
               headers=headers, json=body, timeout=15)
print('Status:', r.status_code)
d = r.json()
new_id = d.get('id', '')
wtn = d.get('latestEvaluation', {}).get('wouldTriggerNow', 'unknown')
print('ID:', new_id)
print('wouldTriggerNow:', wtn)

c = sqlite3.connect('registry.db')
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
c.execute('DELETE FROM strategies WHERE title=?', ('SHORT_INSTANT_1H',))
row = (new_id, 'SHORT_INSTANT_1H', 'BTC 1H RSI below 26', '{}',
       'BTC_USDT_Perp', 'sell', 0.02, 'market', None, 2,
       'GTC', 0, 2000.0, 3.5, 1.0, 'prod', 'active', now, now)
c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
c.commit()
print('OK - SHORT_INSTANT_1H renewed')

print('\n=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
