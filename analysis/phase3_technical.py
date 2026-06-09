"""
Phase 3: BTC technical scoring.

Combines four indicator groups - trend, momentum, price level, volume - all
built from scorer.py's existing indicator functions on the 4H chart, into a
single -10..+10 "phase3_score" with a BULLISH/BEARISH/NEUTRAL verdict.

Group magnitude caps: trend +/-4, momentum +/-3, price level +/-4, volume +/-3
(sum range +/-14), normalized to +/-10 via (A+B+C+D)/14*10.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elfa_grvt_bot.scorer import (
    _klines, _closes, _highs, _lows, _volumes,
    ema, atr, rsi, supertrend_approx, vol_sma,
)

SYMBOL = 'BTCUSDT'
TIMEFRAME = '4h'


def _group_a_trend(k: list) -> Tuple[int, List[str]]:
    """Trend: EMA stack (+/-2) + MACD approx via EMA12/26 & EMA9 signal (+/-1)
    + swing structure over the last 6 candles (+/-1). Max +/-4."""
    closes = _closes(k)
    notes: List[str] = []
    score = 0

    e20, e50, e200 = ema(closes, 20)[-1], ema(closes, 50)[-1], ema(closes, 200)[-1]
    if e20 > e50 > e200:
        score += 2
        notes.append('EMA20>EMA50>EMA200 (bullish stack) -> +2')
    elif e20 < e50 < e200:
        score -= 2
        notes.append('EMA20<EMA50<EMA200 (bearish stack) -> -2')
    else:
        notes.append('EMA stack mixed -> +0')

    ema12, ema26 = ema(closes, 12), ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26) if a is not None and b is not None]
    signal = ema(macd_line, 9)[-1]
    macd_now = macd_line[-1]
    if macd_now > signal:
        score += 1
        notes.append(f'MACD {macd_now:.1f} > signal {signal:.1f} -> +1')
    else:
        score -= 1
        notes.append(f'MACD {macd_now:.1f} <= signal {signal:.1f} -> -1')

    highs, lows = _highs(k), _lows(k)
    higher_high, higher_low = highs[-1] > highs[-3], lows[-1] > lows[-3]
    lower_high, lower_low = highs[-1] < highs[-3], lows[-1] < lows[-3]
    if higher_high and higher_low:
        score += 1
        notes.append('higher-high & higher-low -> +1')
    elif lower_high and lower_low:
        score -= 1
        notes.append('lower-high & lower-low -> -1')
    else:
        notes.append('swing structure mixed -> +0')

    return score, notes


def _group_b_momentum(k: list) -> Tuple[int, List[str]]:
    """Momentum: RSI (+/-2) + Supertrend (+/-1). Max +/-3."""
    closes = _closes(k)
    notes: List[str] = []
    score = 0

    r = rsi(closes, 14)
    if r >= 60:
        score += 2
        notes.append(f'RSI {r:.1f} >= 60 -> +2')
    elif r <= 40:
        score -= 2
        notes.append(f'RSI {r:.1f} <= 40 -> -2')
    else:
        notes.append(f'RSI {r:.1f} neutral (40-60) -> +0')

    st = supertrend_approx(k, 10, 3.0)
    if st == 'long':
        score += 1
        notes.append('Supertrend = long -> +1')
    else:
        score -= 1
        notes.append('Supertrend = short -> -1')

    return score, notes


def _group_c_price_level(k: list, price: float) -> Tuple[int, List[str]]:
    """Price level: position of price within an ATR-padded 20-period high/low
    channel (ATR-based support/resistance). Breakout above/below the channel
    scores the max +/-4; otherwise position within the channel is scaled
    linearly to +/-4."""
    highs, lows = _highs(k), _lows(k)
    atr_vals = atr(k, 14)
    current_atr = next(v for v in reversed(atr_vals) if v is not None)

    lookback = 20
    resistance = max(highs[-lookback:]) + 0.5 * current_atr
    support = min(lows[-lookback:]) - 0.5 * current_atr
    band = resistance - support
    notes = [f'support={support:.1f} resistance={resistance:.1f} price={price:.1f}']

    if band <= 0:
        notes.append('degenerate channel -> +0')
        return 0, notes
    if price >= resistance:
        notes.append('price at/above resistance (breakout) -> +4')
        return 4, notes
    if price <= support:
        notes.append('price at/below support (breakdown) -> -4')
        return -4, notes

    position = (price - support) / band  # 0 = at support, 1 = at resistance
    score = max(-4, min(4, round((position - 0.5) * 8)))
    notes.append(f'channel position {position:.2f} -> {score:+d}')
    return score, notes


def _group_d_volume(k: list) -> Tuple[int, List[str]]:
    """Volume: latest candle's volume vs its 20-period MA, signed by the
    candle's direction (confirms or denies the move). Max +/-3."""
    closes, vols = _closes(k), _volumes(k)
    notes: List[str] = []

    vsma = vol_sma(k, 20)
    ratio = (vols[-1] / vsma) if vsma > 0 else 1.0
    price_up = closes[-1] > closes[-2]
    direction = 1 if price_up else -1
    candle = 'up' if price_up else 'down'

    if ratio >= 1.5:
        score = 3 * direction
        notes.append(f'vol_ratio {ratio:.2f} >= 1.5 on a {candle} candle -> {score:+d}')
    elif ratio >= 1.0:
        score = 1 * direction
        notes.append(f'vol_ratio {ratio:.2f} >= 1.0 on a {candle} candle -> {score:+d}')
    else:
        score = 0
        notes.append(f'vol_ratio {ratio:.2f} < 1.0 (low participation) -> +0')

    return score, notes


def analyze_technical(symbol: str = SYMBOL) -> Dict[str, Any]:
    try:
        k = _klines(symbol, TIMEFRAME, 200)
    except Exception as e:
        return {
            'group_a': 0, 'group_b': 0, 'group_c': 0, 'group_d': 0,
            'phase3_score': 0, 'verdict': 'NEUTRAL',
            'proceed': False, 'error': f'klines_fetch: {e}',
        }

    price = _closes(k)[-1]

    a, notes_a = _group_a_trend(k)
    b, notes_b = _group_b_momentum(k)
    c, notes_c = _group_c_price_level(k, price)
    d, notes_d = _group_d_volume(k)

    raw = (a + b + c + d) / 14 * 10
    phase3_score = max(-10.0, min(10.0, raw))

    if phase3_score >= 5:
        verdict = 'BULLISH'
    elif phase3_score <= -5:
        verdict = 'BEARISH'
    else:
        verdict = 'NEUTRAL'

    return {
        'symbol': symbol,
        'price': price,
        'group_a': a, 'group_a_notes': notes_a,
        'group_b': b, 'group_b_notes': notes_b,
        'group_c': c, 'group_c_notes': notes_c,
        'group_d': d, 'group_d_notes': notes_d,
        'phase3_score': round(phase3_score, 3),
        'verdict': verdict,
        'proceed': True,
    }


if __name__ == '__main__':
    print(json.dumps(analyze_technical(), indent=2, ensure_ascii=False))
