import sqlite3, httpx, pathlib, json
from datetime import datetime

# 問題のあるクエリID（Elfa側でtriggered済み）
TRIGGERED_IDS = [
    '566ca45d-238d-45cb-99be-9653149d0a6d',  # BEAR_EMA200_4H
    'c560bcf0-80e1-4f77-b0ec-9ac8382fd904',  # BEAR_EMA50_1H
    '452acb14-562c-4e6b-941d-8e3f4629f4cb',  # BEAR_MOMENTUM_4H
    'fba2d60a-1e10-4e13-98fd-ba535788776a',  # Q3-SHORT_SETUP_15m
]

env = {}
for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
key = env.get('ELFA_API_KEY', '')
headers = {'x-elfa-api-key': key, 'Content-Type': 'application/json'}

c = sqlite3.connect('registry.db')
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

# 旧クエリのtitle/side情報を保存してから削除
old_info = {}
for qid in TRIGGERED_IDS:
    row = c.execute('SELECT title, side FROM strategies WHERE query_id=?', (qid,)).fetchone()
    if row:
        old_info[qid] = {'title': row[0], 'side': row[1]}
    c.execute('DELETE FROM strategies WHERE query_id=?', (qid,))
    print('Deleted:', qid[:8], '->', old_info.get(qid, {}).get('title', '?'))

c.commit()

# 新規クエリを作成（crosses条件で即時ループを防ぐ）
new_queries = [
    ('BEAR_EMA200_4H',   'BTC 4H EMA200 Bear v2',   'sell',
     {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14}, 'operator': 'crosses_below', 'value': 48}]},
      'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC 4H RSI crosses below 48'}}],
      'expiresIn': '168h'}),
    ('BEAR_EMA50_1H',    'BTC 1H EMA50 Bear v2',    'sell',
     {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 14}, 'operator': 'crosses_below', 'value': 55}]},
      'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC 1H RSI crosses below 55'}}],
      'expiresIn': '168h'}),
    ('BEAR_MOMENTUM_4H', 'BTC 4H Momentum Bear v2', 'sell',
     {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 14}, 'operator': 'crosses_below', 'value': 45}]},
      'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC 4H RSI crosses below 45'}}],
      'expiresIn': '168h'}),
    ('SHORT_SETUP_15m',  'BTC 15m Short Setup v3',  'sell',
     {'conditions': {'AND': [{'source': 'ta', 'method': 'rsi', 'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14}, 'operator': 'crosses_below', 'value': 42}]},
      'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BTC 15m RSI crosses below 42'}}],
      'expiresIn': '168h'}),
]

added = 0
for role, title, side, qbody in new_queries:
    r = httpx.post('https://api.elfa.ai/v2/auto/queries', headers=headers,
                   json={'title': title, 'description': title, 'query': qbody}, timeout=15)
    if r.status_code == 201:
        new_id = r.json().get('id', '')
        wo = (r.json().get('latestEvaluation') or {}).get('wouldTriggerNow', 'unknown')
        row = (new_id, role, title, json.dumps(qbody), 'BTC_USDT_Perp', side,
               0.02, 'market', None, 2, 'GTC', 0, 500.0, 3.5, 1.0, 'prod', 'active', now, now)
        c.execute('INSERT INTO strategies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
        print('OK', role, '->', new_id[:8], 'wouldTrigger=' + str(wo))
        added += 1
    else:
        print('ERR', role, r.status_code, r.text[:80])

c.commit()
print('\nAdded:', added)
print('\n=== Final DB ===')
for row in c.execute('SELECT title, status FROM strategies'):
    print(row)
c.close()
