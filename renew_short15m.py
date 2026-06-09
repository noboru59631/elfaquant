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
    'title': 'BTC 15m Short Setup v5',
    'description': 'BTC 15m RSI crosses below 42',
    'query': {
        'conditions': {'AND': [{
            'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14},
            'operator': 'crosses_below', 'value': 42
        }]},
        'actions': [{'stepId': 'step_1', 'type': 'notify',
                     'params': {'message': 'BTC 15m RSI short setup v5'}}],
        'expiresIn': '168h'
    }
}

r = httpx.post('https://api.elfa.ai/v2/auto/queries',
               headers=headers, json=body, timeout=15)
print('Status:', r.status_code)
new_id = r.json().get('id', '')
print('New ID:', new_id)
wo = r.json().get('latestEvaluation', {}).get('wouldTriggerNow', 'unknown')
print('wouldTriggerNow:', wo)

if new_id:
    c = sqlite3.connect('registry.db')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("DELETE FROM strategies WHERE title='SHORT_SETUP_15m'")
    print('Deleted old SHORT_SETUP_15m rows:', c.execute('SELECT changes()').fetchone()[0])
    row = (new_id, 'SHORT_SETUP_15m', 'BTC 15m RSI crosses below 42', '{}',
           'BTC_USDT_Perp', 'sell', 0.02, 'market', None, 2, 'GTC',
           0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
    c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
    c.commit()
    print('OK - SHORT_SETUP_15m renewed')
    print()
    print('=== Final DB ===')
    for row in c.execute('SELECT title, status FROM strategies'):
        print(row)
    c.close()
