"""
Phase 1: BTC market regime detection.

Classifies the current BTC market regime from the 1D chart's EMA structure
and ATR volatility (scorer.py's existing indicator functions, same data
source/methodology as the bot's live scoring engine). The 4H chart's
supertrend/RSI are computed as supplementary context for later phases.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elfa_grvt_bot.scorer import _klines, _closes, ema, rsi, atr, supertrend_approx

SYMBOL = 'BTCUSDT'

REGIME_TREND_UP   = 'TREND_UP'
REGIME_TREND_DOWN = 'TREND_DOWN'
REGIME_RANGE      = 'RANGE'
REGIME_HIGH_VOL   = 'HIGH_VOL'

ATR_AVG_PERIOD      = 30
HIGH_VOL_MULTIPLIER = 1.5


def detect_regime(symbol: str = SYMBOL) -> Dict[str, Any]:
    """
    Determine the BTC market regime from the 1D and 4H charts.

    Decision order (HIGH_VOL takes priority over the trend classification):
      1. ATR(1D, 14) > 1.5 * (30-day average ATR(1D, 14))  -> HIGH_VOL
      2. EMA20 > EMA50 > EMA200 (1D)                        -> TREND_UP
      3. EMA20 < EMA50 < EMA200 (1D)                        -> TREND_DOWN
      4. otherwise                                          -> RANGE
    """
    try:
        k1d = _klines(symbol, '1d', 250)
        k4h = _klines(symbol, '4h', 200)
    except Exception as e:
        return {
            'regime': None, 'macro_score': 0,
            'ema20': None, 'ema50': None, 'ema200': None,
            'atr': None, 'atr_avg30': None,
            'proceed': False,
            'error': f'klines_fetch: {e}',
        }

    closes_1d = _closes(k1d)
    ema20  = ema(closes_1d, 20)[-1]
    ema50  = ema(closes_1d, 50)[-1]
    ema200 = ema(closes_1d, 200)[-1]

    atr_vals = atr(k1d, 14)
    recent_atr = [v for v in atr_vals if v is not None][-ATR_AVG_PERIOD:]
    current_atr: Optional[float] = recent_atr[-1] if recent_atr else None
    atr_avg30: Optional[float] = (sum(recent_atr) / len(recent_atr)) if recent_atr else None

    # Supplementary 4H context (not part of the regime decision criteria above;
    # carried through for later phases to build on).
    closes_4h = _closes(k4h)
    rsi_4h = rsi(closes_4h, 14)
    supertrend_4h = supertrend_approx(k4h, 10, 3.0)

    if current_atr is not None and atr_avg30 and current_atr > atr_avg30 * HIGH_VOL_MULTIPLIER:
        regime = REGIME_HIGH_VOL
    elif ema20 is not None and ema50 is not None and ema200 is not None and ema20 > ema50 > ema200:
        regime = REGIME_TREND_UP
    elif ema20 is not None and ema50 is not None and ema200 is not None and ema20 < ema50 < ema200:
        regime = REGIME_TREND_DOWN
    else:
        regime = REGIME_RANGE

    return {
        'regime':        regime,
        'macro_score':   0,  # TODO: extend with real macro scoring (sentiment, dominance, etc.)
        'ema20':         ema20,
        'ema50':         ema50,
        'ema200':        ema200,
        'atr':           current_atr,
        'atr_avg30':     atr_avg30,
        'proceed':       True,
        'rsi_4h':        rsi_4h,
        'supertrend_4h': supertrend_4h,
    }


if __name__ == '__main__':
    print(json.dumps(detect_regime(), indent=2, ensure_ascii=False))
