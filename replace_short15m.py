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
    'title': 'BTC 15m RSI Short Setup v2',
    'description': 'BTC 15m RSI crosses below 40',
    'query': {
        'conditions': {'AND': [{'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14}, 'operator': 'crosses_below', 'value': 40}]},
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC 15m RSI short setup'}}],
        'expiresIn': '168h'
    }
}

r = httpx.post('https://api.elfa.ai/v2/auto/queries', headers=headers, json=body, timeout=15)
print('API status:', r.status_code)
new_id = r.json().get('id', '')
print('New ID:', new_id)

if new_id:
    c = sqlite3.connect('registry.db')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE strategies SET status='active' WHERE status='fired'")
    print('fired reset:', c.execute('SELECT changes()').fetchone()[0])
    c.execute("UPDATE strategies SET query_id=?, updated_at=? WHERE title='Q3-SHORT_SETUP_15m'", (new_id, now))
    print('updated rows:', c.execute('SELECT changes()').fetchone()[0])
    c.commit()
    print('')
    print('=== Final DB ===')
    for row in c.execute('SELECT query_id, title, status FROM strategies'):
        print(row)
    c.close()
else:
    print('ERROR: no ID returned')
    print(r.text)
