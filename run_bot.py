import subprocess, sys, sqlite3, httpx, pathlib
from datetime import datetime

# --- fired クエリ自動更新 ---
env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

TEMPLATES = {
    'SHORT_SETUP_15m': {
        'description': 'BTC 15m RSI crosses below 42',
        'query': {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14},
            'operator': 'crosses_below', 'value': 42}]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 15m RSI crosses below 42'}}],
            'expiresIn': '168h'}
    },
    'BEAR_RSI_CROSS_35': {
        'description': 'BTC 1H RSI crosses below 35',
        'query': {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14},
            'operator': 'crosses_below', 'value': 35}]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 1H RSI crosses below 35'}}],
            'expiresIn': '168h'}
    },
    'BEAR_FILTER_SHORT_V2': {
        'description': 'BTC 4H RSI crosses below 40',
        'query': {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14},
            'operator': 'crosses_below', 'value': 40}]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 4H RSI crosses below 40'}}],
            'expiresIn': '168h'}
    },
    'SHORT_REVERSAL_V2': {
        'description': 'BTC 4H RSI crosses below 45',
        'query': {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14},
            'operator': 'crosses_below', 'value': 45}]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 4H RSI crosses below 45'}}],
            'expiresIn': '168h'}
    },
    'BEAR_EMA200_4H': {
        'description': 'BTC 4H RSI crosses below 48',
        'query': {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14},
            'operator': 'crosses_below', 'value': 48}]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 4H RSI crosses below 48'}}],
            'expiresIn': '168h'}
    },
    'BEAR_EMA50_1H': {
        'description': 'BTC 1H RSI crosses below 45',
        'query': {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14},
            'operator': 'crosses_below', 'value': 45}]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 1H RSI crosses below 45'}}],
            'expiresIn': '168h'}
    },
    'BEAR_MOMENTUM_4H': {
        'description': 'BTC 4H RSI crosses below 50',
        'query': {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi',
            'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14},
            'operator': 'crosses_below', 'value': 50}]},
            'actions': [{'stepId': 'step_1', 'type': 'notify',
                         'params': {'message': 'BTC 4H RSI crosses below 50'}}],
            'expiresIn': '168h'}
    },
}

c = sqlite3.connect('registry.db')
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
fired = list(c.execute("SELECT query_id, title FROM strategies WHERE status='fired'"))

if fired:
    print(f'[run_bot] Renewing {len(fired)} fired strategies...')
    for qid, title in fired:
        if title not in TEMPLATES:
            print(f'  SKIP {title}')
            continue
        tmpl = TEMPLATES[title]
        body = {'title': f'{title} auto', **tmpl}
        r = httpx.post('https://api.elfa.ai/v2/auto/queries',
                       headers=headers, json=body, timeout=15)
        if r.status_code == 201:
            new_id = r.json().get('id', '')
            c.execute('DELETE FROM strategies WHERE query_id=?', (qid,))
            row = (new_id, title, tmpl['description'], '{}',
                   'BTC_USDT_Perp', 'sell', 0.02, 'market', None, 2,
                   'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
            c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
            c.commit()
            print(f'  OK {title}: {qid[:8]} -> {new_id[:8]}')
        else:
            print(f'  ERROR {title}: {r.text[:100]}')
else:
    print('[run_bot] No fired strategies, starting bot directly...')

c.close()

# --- ボット起動 ---
print('[run_bot] Starting bot...')
subprocess.run([sys.executable, '-m', 'elfa_grvt_bot.cli', 'run'])
