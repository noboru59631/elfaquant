"""
Phase 2: BTC fundamentals/derivatives scoring.

Scores funding rate, open-interest dynamics, and (placeholder) exchange
netflow into a single -10..+10 "phase2_score" with a BULLISH/BEARISH/NEUTRAL
verdict. Reuses scorer.py's existing Binance fetchers for funding rate, open
interest and the 24h ticker (same data source/methodology as the live bot).
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from elfa_grvt_bot.scorer import BINANCE_BASE, _funding_rate, _open_interest, _ticker_24h

SYMBOL = 'BTCUSDT'

# Matches the funding-rate threshold scorer.py's compute_scores already treats as "neutral".
FUNDING_NEUTRAL_BAND = 0.0001


def _oi_change_pct(symbol: str, period: str = '1d', limit: int = 2) -> float:
    """% change in aggregate open interest over the most recent `period` window.

    scorer._open_interest only returns a point-in-time snapshot, so OI direction
    needs a second data point - Binance's public open-interest history endpoint.
    """
    url = f'{BINANCE_BASE}/futures/data/openInterestHist'
    r = httpx.get(url, params={'symbol': symbol, 'period': period, 'limit': limit}, timeout=15)
    r.raise_for_status()
    data = r.json()
    if len(data) < 2:
        return 0.0
    oldest = float(data[0]['sumOpenInterest'])
    newest = float(data[-1]['sumOpenInterest'])
    if oldest == 0:
        return 0.0
    return (newest - oldest) / oldest * 100


def _funding_score(funding_rate: float) -> int:
    if funding_rate < -FUNDING_NEUTRAL_BAND:
        return 3   # shorts pay longs -> contrarian bullish
    if funding_rate > FUNDING_NEUTRAL_BAND:
        return -3  # longs pay shorts -> contrarian bearish
    return 0


def _oi_score(price_change_pct: float, oi_change_pct: float) -> int:
    price_up, price_down = price_change_pct > 0, price_change_pct < 0
    oi_up, oi_down = oi_change_pct > 0, oi_change_pct < 0

    if price_up and oi_up:
        return 3    # fresh longs entering -> bullish continuation
    if price_down and oi_down:
        return 2    # positions unwinding into the drop -> bearish exhaustion
    if price_down and oi_up:
        return -3   # fresh shorts entering -> bearish continuation
    return 0        # price up & OI down (long unwind), or flat/ambiguous -> no clear signal


def analyze_fundamentals(symbol: str = SYMBOL) -> Dict[str, Any]:
    try:
        funding_rate  = _funding_rate(symbol)
        open_interest = _open_interest(symbol)
        ticker        = _ticker_24h(symbol)
        oi_change_pct = _oi_change_pct(symbol)
    except Exception as e:
        return {
            'funding_score': 0, 'oi_score': 0, 'netflow_score': 0,
            'phase2_score': 0, 'verdict': 'NEUTRAL',
            'proceed': False, 'error': f'fundamentals_fetch: {e}',
        }

    price_change_pct = float(ticker.get('priceChangePercent', 0) or 0)

    funding_score = _funding_score(funding_rate)
    oi_score      = _oi_score(price_change_pct, oi_change_pct)
    netflow_score = 0  # TODO: wire up an exchange-netflow data source

    raw = funding_score * 0.4 + oi_score * 0.4 + netflow_score * 0.2
    phase2_score = max(-10.0, min(10.0, raw))

    if phase2_score >= 5:
        verdict = 'BULLISH'
    elif phase2_score <= -5:
        verdict = 'BEARISH'
    else:
        verdict = 'NEUTRAL'

    return {
        'symbol':            symbol,
        'funding_rate':      funding_rate,
        'funding_score':     funding_score,
        'open_interest':     open_interest,
        'oi_change_pct':     round(oi_change_pct, 3),
        'oi_score':          oi_score,
        'price_change_pct':  price_change_pct,
        'netflow_score':     netflow_score,
        'phase2_score':      round(phase2_score, 3),
        'verdict':           verdict,
        'proceed':           True,
    }


if __name__ == '__main__':
    print(json.dumps(analyze_fundamentals(), indent=2, ensure_ascii=False))
