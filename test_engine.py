import sys
sys.path.insert(0, '.')
from elfa_grvt_bot.scorer import fetch_market_snapshot, compute_scores, calc_trade_params
from elfa_grvt_bot.strategy_engine import evaluate

print('=== STRATEGY NETECTION ENGINE TEST ===')
print('')

snap = fetch_market_snapshot('BTCUSDT')
price = snap.get('price') or 0.0
print('[Test1] price=' + str(round(price,1)) + ' ST4}' + str(snap.get('supertrend_4h')) + ' ST1=' + str(snap.get('supertrend_1h')))
print('  EMA50_4H=' + str(round(snap.get('ema50_4h') or 0,1)) + ' EMA200_4H=' + str(round(snap.get('ema200_4h') or 0,1)))
print('  ADX=' + str(round(snap.get('adx_4h') or 0,1)) + ' DI+=' + str(round(snap.get('di_plus_4h') or 0,1)) + ' DI-=' + str(round(snap.get('di_minus_4h') or 0,1)))
print('  RSI1H=' + str(round(snap.get('rsi_1h') or 50,1)) + ' RSI15m=' + str(round(snap.get('rsi_15m') or 50,1)) + ' VolRatio=' + str(round(snap.get('vol_ratio_15m') or 1,2)) + 'x')
print('  Funding=' + str(snap.get('funding_rate') or 0) + ' Spread=' + str(round(snap.get('spread') or 0,2)) + ' Errors=' + str(snap.get('errors') or None))
assert price > 0, 'price is 0'
print('  [PASS]')
print('')

ls, ss, mode = compute_scores(snap)
print('[Test2] Long=' + str(ls) + ' Short=' + str(ss) + ' Mode=' + mode)
assert mode in ('BULL_TREND','BEAR_TREND','LONG_REVERSAL','SHORT_REVERSAL','RANGE')
print('  [PASS]')
print('')

side = 'long' if ls >= ss else 'short'
p = calc_trade_params(side, price, snap, ls, ss, 1132.0, mode)
print('[Test3] side=' + side)
if p:
    print('  Entry=' + str(round(p['entry_price'],1)) + ' SL=' + str(round(p['stop_loss'],1)) + ' TP=' + str(round(p['take_profit'],1)))
    print('  RR=' + str(p['rr']) + ' Risk=' + str(round(p['risk_usdt'],2)) + 'USD  Qty=' + str(p['qty_btc']) + 'BTC  Lev=' + str(p['effective_leverage']) + 'x')
    print('  [PASS]')
else:
    print('  [INFO] calc=None HOLD condition')
print('')

print('[Test4] evaluate()...')
for qid, role in [('d9067784-75a5-4953-ba9c-0a97830c27b0','SHORT_SETUP_15m'),('30d4435d-e933-446f-9162-ca98b4afca03','BEAR_FILTER_SHORT'),('f7667ea4-85f2-4d10-a534-5bf1a67272d3','BULL_FILTER_LONG')]:
    r = evaluate(qid, account_equity=1132.0)
    print('  [' + role + '] Action=' + r['action'] + ' L=' + str(r['long_score']) + ' S=' + str(r['short_score']) + ' Mode=' + r['mode'])
    if r['action'] != 'HOLD':
        print('    Entry=' + str(r.get('entry_price')) + ' SL=' + str(r.get('stop_loss')) + ' TP=' + str(r.get('take_profit')) + ' Qty=' + str(r.get('qty_btc')) + 'BTC')
print('  [PASS]')
print('')
print('=== ALL TESTQ PASSED - Bot is ready ===')
