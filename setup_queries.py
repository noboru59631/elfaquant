import httpx, json, os, sys, sqlite3, time

# .env読み込み
with open('.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

API_KEY = os.environ.get('ELFA_API_KEY', '')
HEADERS = {'x-elfa-api-key': API_KEY, 'Content-Type': 'application/json'}
BASE = 'https://api.elfa.ai'

def validate_and_create(payload, name):
    print(f'\n=== {name} ===')
    r = httpx.post(f'{BASE}/v2/auto/queries/validate', json=payload, headers=HEADERS, timeout=30)
    v = r.json()
    if not v.get('valid'):
        print(f'INVALID: {v}')
        return None
    print('Validate: OK')
    time.sleep(1)
    r2 = httpx.post(f'{BASE}/v2/auto/queries', json=payload, headers=HEADERS, timeout=30)
    if r2.status_code not in (200, 201):
        print(f'Create failed: {r2.status_code} {r2.text}')
        return None
    qid = r2.json().get('id')
    print(f'Created: {qid}')
    return qid

# =============================================
# Query 1: 4H上位足トレンドフィルター
# BTC価格がEMA50を上抜け or 下抜け（webhook通知）
# =============================================
q1_long = {
    'title': 'BTC 4H Bull Filter - Price crosses above EMA50',
    'description': 'Upper timeframe bull trend confirmation: BTC 4H price crosses above EMA50. Used as BULL_TREND filter for entry scoring.',
    'query': {
        'conditions': {
            'AND': [
                {
                    'source': 'price',
                    'method': 'current',
                    'args': {'symbol': 'BTC'},
                    'operator': 'crosses_above',
                    'value': {
                        'source': 'ta',
                        'method': 'ema',
                        'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 50}
                    }
                }
            ]
        },
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BULL_FILTER_ACTIVE: BTC 4H price crossed above EMA50'}}],
        'expiresIn': '7d'
    }
}

q1_short = {
    'title': 'BTC 4H Bear Filter - Price crosses below EMA50',
    'description': 'Upper timeframe bear trend confirmation: BTC 4H price crosses below EMA50. Used as BEAR_TREND filter for entry scoring.',
    'query': {
        'conditions': {
            'AND': [
                {
                    'source': 'price',
                    'method': 'current',
                    'args': {'symbol': 'BTC'},
                    'operator': 'crosses_below',
                    'value': {
                        'source': 'ta',
                        'method': 'ema',
                        'args': {'symbol': 'BTC', 'timeframe': '4h', 'period': 50}
                    }
                }
            ]
        },
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'BEAR_FILTER_ACTIVE: BTC 4H price crossed below EMA50'}}],
        'expiresIn': '7d'
    }
}

# =============================================
# Query 2: 1H方向転換検知
# EMA20 crosses EMA50 (ゴールデン/デッドクロス)
# =============================================
q2_long = {
    'title': 'BTC 1H Long Reversal - EMA20 crosses above EMA50',
    'description': '1H momentum shift to long: EMA20 crosses above EMA50 on 1H. Signals LONG_REVERSAL mode activation.',
    'query': {
        'conditions': {
            'AND': [
                {
                    'source': 'ta',
                    'method': 'ema',
                    'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 20},
                    'operator': 'crosses_above',
                    'value': {
                        'source': 'ta',
                        'method': 'ema',
                        'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 50}
                    }
                }
            ]
        },
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'LONG_REVERSAL: BTC 1H EMA20 crossed above EMA50'}}],
        'expiresIn': '7d'
    }
}

q2_short = {
    'title': 'BTC 1H Short Reversal - EMA20 crosses below EMA50',
    'description': '1H momentum shift to short: EMA20 crosses below EMA50 on 1H. Signals SHORT_REVERSAL mode activation.',
    'query': {
        'conditions': {
            'AND': [
                {
                    'source': 'ta',
                    'method': 'ema',
                    'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 20},
                    'operator': 'crosses_below',
                    'value': {
                        'source': 'ta',
                        'method': 'ema',
                        'args': {'symbol': 'BTC', 'timeframe': '1h', 'period': 50}
                    }
                }
            ]
        },
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'SHORT_REVERSAL: BTC 1H EMA20 crossed below EMA50'}}],
        'expiresIn': '7d'
    }
}

# =============================================
# Query 3: 15m エントリー候補検知
# 価格がEMA20に接触後、RSIが40を上抜け（押し目買いセットアップ）
# 価格がEMA20に接触後、RSIが60を下抜け（戻り売りセットアップ）
# =============================================
q3_long = {
    'title': 'BTC 15m Long Setup - RSI crosses above 40 near EMA20',
    'description': '15m pullback buy setup: BTC RSI crosses above 40 while price is above EMA50 on 15m. Candidate for long entry scoring.',
    'query': {
        'conditions': {
            'AND': [
                {
                    'source': 'ta',
                    'method': 'rsi',
                    'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14},
                    'operator': 'crosses_above',
                    'value': 40
                },
                {
                    'source': 'price',
                    'method': 'current',
                    'args': {'symbol': 'BTC'},
                    'operator': '>',
                    'value': {
                        'source': 'ta',
                        'method': 'ema',
                        'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 50}
                    }
                }
            ]
        },
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'LONG_SETUP: BTC 15m RSI crossed above 40 with price above EMA50'}}],
        'expiresIn': '7d'
    }
}

q3_short = {
    'title': 'BTC 15m Short Setup - RSI crosses below 60 near EMA20',
    'description': '15m pullback sell setup: BTC RSI crosses below 60 while price is below EMA50 on 15m. Candidate for short entry scoring.',
    'query': {
        'conditions': {
            'AND': [
                {
                    'source': 'ta',
                    'method': 'rsi',
                    'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 14},
                    'operator': 'crosses_below',
                    'value': 60
                },
                {
                    'source': 'price',
                    'method': 'current',
                    'args': {'symbol': 'BTC'},
                    'operator': '<',
                    'value': {
                        'source': 'ta',
                        'method': 'ema',
                        'args': {'symbol': 'BTC', 'timeframe': '15m', 'period': 50}
                    }
                }
            ]
        },
        'actions': [{'stepId': 'step_1', 'type': 'notify', 'params': {'message': 'SHORT_SETUP: BTC 15m RSI crossed below 60 with price below EMA50'}}],
        'expiresIn': '7d'
    }
}

queries = [
    (q1_long,  'Q1-BULL_FILTER_LONG'),
    (q1_short, 'Q1-BEAR_FILTER_SHORT'),
    (q2_long,  'Q2-LONG_REVERSAL'),
    (q2_short, 'Q2-SHORT_REVERSAL'),
    (q3_long,  'Q3-LONG_SETUP_15m'),
    (q3_short, 'Q3-SHORT_SETUP_15m'),
]

results = {}
for payload, name in queries:
    qid = validate_and_create(payload, name)
    results[name] = qid
    time.sleep(2)

print('\n\n========== 登録結果 ==========')
for name, qid in results.items():
    status = qid if qid else 'FAILED'
    print(f'{name}: {status}')

# registry.dbに保存
db = 'registry.db'
with sqlite3.connect(db) as conn:
    for name, qid in results.items():
        if qid:
            conn.execute('''INSERT OR IGNORE INTO strategies
                (query_id, title, description, eql_json, symbol, side, amount,
                 order_type, price, leverage, time_in_force, reduce_only,
                 max_notional_usd, tp_pct, sl_pct, env, status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))''',
                (qid, name, name, '{}', 'BTC_USDT_Perp',
                 'buy' if 'LONG' in name else 'sell',
                 0.001, 'market', None, 2, 'GTC', 0, 500.0, 2.0, 1.0, 'prod', 'active'))
    conn.commit()
print('\nRegistry saved. Done.')