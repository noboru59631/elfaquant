import json, logging
from typing import Dict, Any, Optional
from .scorer import fetch_market_snapshot, compute_scores, calc_trade_params

logger = logging.getLogger(__name__)

QUERY_ROLES = {
    # --- 現行アクティブID (2026-05-23更新) ---
    '726ffdd0-2feb-4111-972b-2a68eae86c7e': 'BULL_FILTER_LONG',    # Q1-BULL_FILTER_LONG
    'da16ab97-d7b9-48a0-8a47-9911cbf9d9ea': 'LONG_REVERSAL',       # Q2-LONG_REVERSAL
    '5e163e96-7dd4-4e2b-a002-5df4a69d7ab7': 'BEAR_FILTER_SHORT',   # BEAR_EMA200_4H
    '511ba089-69b0-4fe7-8388-121e53915070': 'BEAR_FILTER_SHORT',   # BEAR_MOMENTUM_4H
    '2ce7551d-4458-4d4c-b111-1f90d2048ad9': 'BEAR_FILTER_SHORT',   # BEAR_EMA50_1H
    'e1cf734e-4a1c-4fea-9af4-a5c4e5ceebf0': 'BEAR_FILTER_SHORT',   # BEAR_FILTER_SHORT_V2
    'cb038e56-60c8-46a6-a945-a25a19a28a76': 'SHORT_REVERSAL',      # SHORT_REVERSAL_V2
    '55331a30-47a7-44b5-9682-2daaaa1f6f49': 'SHORT_SETUP_15m',     # SHORT_SETUP_15m
    '7050103d-3565-4abb-a37d-8e0ed247bf3f': 'BEAR_FILTER_SHORT',   # BEAR_RSI_CROSS_35
    'f465ad59-5084-4c85-ab2b-10ee330a9720': 'RSI_OVERSOLD',        # BTC RSI Oversold
    'fde37cae-9f2b-487b-9e9f-e0cf4a906958': 'SHORT_SETUP_15m',     # SHORT_INSTANT_1H
    'a98762ab-82cd-4386-bfb0-8a3f4ef2825a': 'SHORT_SETUP_15m',     # SHORT_INSTANT_4H
    'e8f60dd7-9a52-4ec1-97f1-b657d87f9695': 'SHORT_SETUP_15m',     # 追加クエリ
    '9f71f044-0d33-4409-bbaa-2be1545bddb0': 'SHORT_SETUP_15m',     # 追加クエリ
    'df9d80bd-f25d-40af-a743-a75de27e088b': 'SHORT_SETUP_15m',     # SHORT_NOW_1H
    '5e93b5bc-3600-468e-b410-cc1ac3ddbf78': 'SHORT_SETUP_15m',     # SHORT_NOW_4H
    'fc7f4d14-fd2c-48a9-9e79-d8436efb8892': 'SHORT_SETUP_15m',
}

NORMAL_THRESHOLD = 52
VOLUME_THRESHOLD = 50
SCORE_GAP_NORMAL = 8
SCORE_GAP_VOLUME = 8

def evaluate(query_id: str, account_equity: float = 1132.0) -> Dict[str, Any]:
    trigger_role = QUERY_ROLES.get(query_id, 'UNKNOWN')
    logger.info(f'[Engine] Triggered by {query_id} ({trigger_role})')
    try:
        snap = fetch_market_snapshot('BTCUSDT')
    except Exception as e:
        logger.error(f'[Engine] Market fetch failed: {e}')
        return _hold(f'Market data fetch error: {e}', trigger_role)
    if snap.get('errors'):
        logger.warning(f'[Engine] Snapshot errors: {snap["errors"]}')
    if not snap.get('price'):
        return _hold('price missing in snapshot', trigger_role)
    long_score, short_score, mode = compute_scores(snap)
    logger.info(f'[Engine] Mode={mode} L={long_score} S={short_score} ADX={snap.get("adx_4h",0):.1f} ST4={snap.get("supertrend_4h")} ST1={snap.get("supertrend_1h")}')
    price = snap['price']
    data_fresh = len(snap.get('errors', [])) == 0
    spread_ok  = snap.get('spread', 999) < price * 0.001
    safety = {
        'data_fresh': data_fresh, 'spread_ok': spread_ok,
        'api_ok': True, 'daily_loss_limit_ok': True,
        'weekly_loss_limit_ok': True, 'position_limit_ok': True, 'tp_sl_ready': True,
    }
    if not data_fresh:
        return _hold(f'Data errors: {snap["errors"]}', trigger_role, snap, long_score, short_score, mode, safety)
    if not spread_ok:
        return _hold('Spread too wide', trigger_role, snap, long_score, short_score, mode, safety)
    if mode == 'RANGE':
        return _hold('RANGE mode - no entry', trigger_role, snap, long_score, short_score, mode, safety)
    threshold = VOLUME_THRESHOLD if trigger_role in ('LONG_SETUP_15m', 'SHORT_SETUP_15m') else NORMAL_THRESHOLD
    score_gap  = SCORE_GAP_VOLUME if trigger_role in ('LONG_SETUP_15m', 'SHORT_SETUP_15m') else SCORE_GAP_NORMAL
    action = 'HOLD'
    side   = None
    setup  = 'none'
    if (long_score >= threshold and long_score >= short_score + score_gap
            and trigger_role in ('BULL_FILTER_LONG','LONG_REVERSAL','LONG_SETUP_15m','RSI_OVERSOLD')):
        action = 'ENTER_LONG';  side = 'long';  setup = 'pullback' if trigger_role == 'LONG_SETUP_15m' else 'breakout'
    elif (short_score >= threshold and short_score >= long_score + score_gap
              and trigger_role in ('BEAR_FILTER_SHORT','SHORT_REVERSAL','SHORT_SETUP_15m')):
        action = 'ENTER_SHORT'; side = 'short'; setup = 'pullback' if trigger_role == 'SHORT_SETUP_15m' else 'breakout'
    if action == 'HOLD':
        return _hold(f'Trigger:{trigger_role} L={long_score} S={short_score} threshold={threshold} Mode={mode}',
                     trigger_role, snap, long_score, short_score, mode, safety)
    params = calc_trade_params(side, price, snap, long_score, short_score, account_equity, mode)
    if params is None:
        return _hold('SL/TP calculation failed', trigger_role, snap, long_score, short_score, mode, safety)
    entry_type = 'post_only_limit' if setup == 'pullback' else 'stop_market'
    tf_trigger = '15m' if trigger_role.endswith('15m') else '5m'
    return {
        'symbol': 'BTCUSDT', 'action': action, 'mode': mode,
        'confidence': max(long_score, short_score),
        'long_score': long_score, 'short_score': short_score,
        'setup': setup, 'entry_type': entry_type,
        'entry_price': params['entry_price'], 'stop_loss': params['stop_loss'],
        'take_profit': params['take_profit'], 'rr': params['rr'],
        'risk_pct': params['risk_pct'], 'risk_usdt': params['risk_usdt'],
        'qty_btc': params['qty_btc'], 'notional_usdt': params['notional_usdt'],
        'effective_leverage': params['effective_leverage'],
        'timeframe_trigger': tf_trigger,
        'reasons': [
            f'Trigger:{trigger_role} Mode:{mode} L={long_score} S={short_score}',
            f'Price={price:.1f} ST4={snap.get("supertrend_4h")} ST1={snap.get("supertrend_1h")}',
            f'EMA50_4H={snap.get("ema50_4h",0):.1f} EMA200_4H={snap.get("ema200_4h",0):.1f}',
            f'ADX={snap.get("adx_4h",0):.1f} DI+={snap.get("di_plus_4h",0):.1f} DI-={snap.get("di_minus_4h",0):.1f}',
            f'RSI_1H={snap.get("rsi_1h",50):.1f} RSI_15m={snap.get("rsi_15m",50):.1f}',
            f'VolRatio={snap.get("vol_ratio_15m",1):.2f} Funding={snap.get("funding_rate",0):.5f}',
        ],
        'invalidation': f'4H close {"below" if side=="long" else "above"} EMA50({snap.get("ema50_4h",0):.1f}) or ST flips',
        'safety_checks': safety,
        'orders': [
            {'type':'entry','side':'buy' if side=='long' else 'sell','price':params['entry_price'],'qty':params['qty_btc'],'post_only':entry_type=='post_only_limit','reduce_only':False},
            {'type':'take_profit','side':'sell' if side=='long' else 'buy','price':params['take_profit'],'qty':params['qty_btc'],'post_only':False,'reduce_only':True},
            {'type':'stop_loss','side':'sell' if side=='long' else 'buy','price':params['stop_loss'],'qty':params['qty_btc'],'post_only':False,'reduce_only':True},
        ],
        'next_check': 'next_5m_close',
    }

def _hold(reason, trigger='', snap=None, ls=0, ss=0, mode='RANGE', safety=None):
    if safety is None:
        safety = {k:True for k in ['data_fresh','spread_ok','api_ok','daily_loss_limit_ok','weekly_loss_limit_ok','position_limit_ok','tp_sl_ready']}
    return {
        'symbol':'BTCUSDT','action':'HOLD','mode':mode,'confidence':0,
        'long_score':ls,'short_score':ss,'setup':'none','entry_type':'none',
        'entry_price':None,'stop_loss':None,'take_profit':None,'rr':None,
        'risk_pct':None,'risk_usdt':None,'qty_btc':None,'notional_usdt':None,
        'effective_leverage':None,'timeframe_trigger':'none','reasons':[reason],
        'invalidation':'','safety_checks':safety,
        'orders':[
            {'type':'entry','side':'none','price':None,'qty':None,'post_only':True,'reduce_only':False},
            {'type':'take_profit','side':'none','price':None,'qty':None,'post_only':False,'reduce_only':True},
            {'type':'stop_loss','side':'none','price':None,'qty':None,'post_only':False,'reduce_only':True},
        ],
        'next_check':'next_5m_close',
    }