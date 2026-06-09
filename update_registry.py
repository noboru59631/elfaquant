import sqlite3

db_path = 'registry.db'
new_id = '8abea377-9d40-4728-9514-47dc99a720d9'

eql = '{\"conditions\":{\"AND\":[{\"source\":\"ta\",\"method\":\"rsi\",\"args\":{\"symbol\":\"BTC\",\"timeframe\":\"1h\"},\"operator\":\"<\",\"value\":30}]},\"actions\":[{\"stepId\":\"step_1\",\"type\":\"notify\",\"params\":{\"message\":\"BTC RSI oversold - enter long\"}}],\"expiresIn\":\"3d\"}'

with sqlite3.connect(db_path) as conn:
    conn.execute('''INSERT INTO strategies
        (query_id, title, description, eql_json, symbol, side, amount,
         order_type, price, leverage, time_in_force, reduce_only,
         max_notional_usd, tp_pct, sl_pct, env, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))''',
        (new_id, 'BTC RSI Oversold', 'BTC 1h RSI below 30 long entry',
         eql, 'BTC_USDT_Perp', 'buy', 0.001, 'market', None, 2,
         'GTC', 0, 500.0, 2.0, 1.0, 'prod', 'active'))
    conn.commit()
    rows = conn.execute('SELECT query_id, title, status FROM strategies').fetchall()
    for r in rows:
        print(f'ID: {r[0]}')
        print(f'Title: {r[1]}  Status: {r[2]}')
print('OK - registry updated')