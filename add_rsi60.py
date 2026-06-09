import sqlite3, httpx, pathlib, json
from datetime import datetime

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

body = {
    'title': 'BTC 1H RSI Below 65',
    'description': 'BTC 1H RSI below 65 short signal',
    'query': {
        'conditions': {'AND': [
            {'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14}, 'operator': '<', 'value': 65}
        ]},
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC RSI below 65'}}],
        'expiresIn': '168h'
    }
}

r = httpx.post('https://api.elfa.ai/v2/auto/queries', headers=headers, json=body, timeout=15)
print('Status:', r.status_code)
d = r.json()
new_id = d.get('id', '')
print('ID:', new_id)
ev = d.get('latestEvaluation', {})
wo = ev.get('wouldTriggerNow', 'unknown') if ev else 'unknown'
rsi_val = ev.get('matchingConditions', 'unknown') if ev else 'unknown'
print('wouldTriggerNow:', wo)

if new_id:
    c = sqlite3.connect('registry.db')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    row = (new_id, 'RSI_BELOW_65', 'BTC 1H RSI below 65', '{}',
           'BTC_USDT_Perp', 'sell', 0.02, 'market', None, 2,
           'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
    c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
    c.commit()
    print('OK - RSI_BELOW_65 inserted')
    print('')
    print('=== DB ===')
    for row in c.execute('SELECT title, status FROM strategies'):
        print(row)
    c.close()
