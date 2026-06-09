"""
BTC/USDT Perpetual - Multi-timeframe scoring engine
Fetches live data from Binance public API and computes long/short scores.
"""
import httpx
import math
from typing import Dict, Any, Optional, Tuple

BINANCE_BASE = 'https://fapi.binance.com'  # Futures API

# ─────────────────────────────────────────────
# Low-level data fetch
# ─────────────────────────────────────────────

def _klines(symbol: str, interval: str, limit: int = 200) -> list:
    url = f'{BINANCE_BASE}/fapi/v1/klines'
    r = httpx.get(url, params={'symbol': symbol, 'interval': interval, 'limit': limit}, timeout=15)
    r.raise_for_status()
    return r.json()

def _funding_rate(symbol: str) -> float:
    url = f'{BINANCE_BASE}/fapi/v1/premiumIndex'
    r = httpx.get(url, params={'symbol': symbol}, timeout=10)
    r.raise_for_status()
    return float(r.json().get('lastFundingRate', 0))

def _open_interest(symbol: str) -> float:
    url = f'{BINANCE_BASE}/fapi/v1/openInterest'
    r = httpx.get(url, params={'symbol': symbol}, timeout=10)
    r.raise_for_status()
    return float(r.json().get('openInterest', 0))

def _ticker_24h(symbol: str) -> dict:
    # 24h ticker (lastPrice, volume etc.)
    url = f'{BINANCE_BASE}/fapi/v1/ticker/24hr'
    r = httpx.get(url, params={'symbol': symbol}, timeout=10)
    r.raise_for_status()
    data = r.json()
    # bookTicker (ask/bid spread)
    try:
        url2 = f'{BINANCE_BASE}/fapi/v1/ticker/bookTicker'
        r2 = httpx.get(url2, params={'symbol': symbol}, timeout=10)
        book = r2.json()
        data['askPrice'] = book.get('askPrice')
        data['bidPrice']  = book.get('bidPrice')
    except Exception:
        pass
    return data

# ─────────────────────────────────────────────
# Indicator calculations
# ─────────────────────────────────────────────

def _closes(klines): return [float(k[4]) for k in klines]
def _highs(klines):  return [float(k[2]) for k in klines]
def _lows(klines):   return [float(k[3]) for k in klines]
def _volumes(klines):return [float(k[5]) for k in klines]

def ema(prices: list, period: int) -> list:
    k = 2 / (period + 1)
    result = [None] * len(prices)
    for i, p in enumerate(prices):
        if i < period - 1:
            continue
        if i == period - 1:
            result[i] = sum(prices[:period]) / period
        else:
            result[i] = p * k + result[i-1] * (1 - k)
    return result

def atr(klines: list, period: int = 14) -> list:
    highs  = _highs(klines)
    lows   = _lows(klines)
    closes = _closes(klines)
    trs = []
    for i in range(1, len(klines)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i]  - closes[i-1]))
        trs.append(tr)
    atr_vals = [None] * (len(klines))
    atr_vals[period] = sum(trs[:period]) / period
    for i in range(period + 1, len(klines)):
        atr_vals[i] = (atr_vals[i-1] * (period - 1) + trs[i-1]) / period
    return atr_vals

def adx_di(klines: list, period: int = 14) -> Tuple[list, list, list]:
    """Returns (adx, di_plus, di_minus) as lists."""
    highs  = _highs(klines)
    lows   = _lows(klines)
    closes = _closes(klines)
    n = len(klines)

    dm_plus  = [0.0] * n
    dm_minus = [0.0] * n
    trs      = [0.0] * n

    for i in range(1, n):
        up   = highs[i]  - highs[i-1]
        down = lows[i-1] - lows[i]
        dm_plus[i]  = up   if (up > down and up > 0)   else 0.0
        dm_minus[i] = down if (down > up and down > 0) else 0.0
        trs[i] = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i]  - closes[i-1]))

    def smooth(arr, p):
        out = [0.0] * n
        out[p] = sum(arr[1:p+1])
        for i in range(p+1, n):
            out[i] = out[i-1] - out[i-1]/p + arr[i]
        return out

    str14   = smooth(trs,      period)
    sdm_p   = smooth(dm_plus,  period)
    sdm_m   = smooth(dm_minus, period)

    di_p = [0.0] * n
    di_m = [0.0] * n
    dx   = [0.0] * n

    for i in range(period, n):
        di_p[i] = (sdm_p[i] / str14[i] * 100) if str14[i] > 0 else 0
        di_m[i] = (sdm_m[i] / str14[i] * 100) if str14[i] > 0 else 0
        s = di_p[i] + di_m[i]
        dx[i] = abs(di_p[i] - di_m[i]) / s * 100 if s > 0 else 0

    adx_out = [0.0] * n
    adx_out[period * 2] = sum(dx[period:period*2+1]) / (period + 1)
    for i in range(period * 2 + 1, n):
        adx_out[i] = (adx_out[i-1] * (period - 1) + dx[i]) / period

    return adx_out, di_p, di_m

def vwap(klines: list) -> float:
    """Session VWAP (all provided candles)."""
    tp_vol = 0.0
    vol_sum = 0.0
    for k in klines:
        h, l, c, v = float(k[2]), float(k[3]), float(k[4]), float(k[5])
        tp = (h + l + c) / 3
        tp_vol  += tp * v
        vol_sum += v
    return tp_vol / vol_sum if vol_sum > 0 else 0.0

def vol_sma(klines: list, period: int = 20) -> float:
    vols = _volumes(klines)
    if len(vols) < period:
        return 0.0
    return sum(vols[-period:]) / period

def rsi(prices: list, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        d = prices[-period-1+i] - prices[-period-2+i]
        (gains if d > 0 else losses).append(abs(d))
    ag = sum(gains) / period
    al = sum(losses) / period
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)

def supertrend_approx(klines: list, atr_period: int = 10, multiplier: float = 3.0) -> str:
    """
    Supertrend approximation using ATR.
    Returns 'long' or 'short'.
    """
    closes = _closes(klines)
    highs  = _highs(klines)
    lows   = _lows(klines)

    atr_vals = atr(klines, atr_period)
    trend = 'long'
    up_band   = 0.0
    down_band = 0.0

    for i in range(atr_period + 1, len(klines)):
        if atr_vals[i] is None:
            continue
        hl2 = (highs[i] + lows[i]) / 2
        new_up   = hl2 - multiplier * atr_vals[i]
        new_down = hl2 + multiplier * atr_vals[i]

        up_band   = max(new_up,   up_band)   if closes[i-1] > up_band   else new_up
        down_band = min(new_down, down_band) if closes[i-1] < down_band else new_down

        if trend == 'long'  and closes[i] < up_band:   trend = 'short'
        if trend == 'short' and closes[i] > down_band: trend = 'long'

    return trend

# ─────────────────────────────────────────────
# Market data snapshot
# ─────────────────────────────────────────────

def fetch_market_snapshot(symbol: str = 'BTCUSDT') -> Dict[str, Any]:
    snap = {'symbol': symbol, 'errors': []}

    try:
        k4h  = _klines(symbol, '4h',  200)
        k1h  = _klines(symbol, '1h',  200)
        k15m = _klines(symbol, '15m', 100)
        k5m  = _klines(symbol, '5m',  60)
    except Exception as e:
        snap['errors'].append(f'klines_fetch: {e}')
        return snap

    # ── Price ──
    snap['price'] = float(k5m[-1][4])

    # ── EMA ──
    try:
        c4h = _closes(k4h)
        snap['ema20_4h']  = ema(c4h, 20)[-1]
        snap['ema50_4h']  = ema(c4h, 50)[-1]
        snap['ema200_4h'] = ema(c4h, 200)[-1]

        c1h = _closes(k1h)
        snap['ema20_1h']  = ema(c1h, 20)[-1]
        snap['ema50_1h']  = ema(c1h, 50)[-1]
        snap['ema200_1h'] = ema(c1h, 200)[-1]

        c15m = _closes(k15m)
        snap['ema20_15m'] = ema(c15m, 20)[-1]
        snap['ema50_15m'] = ema(c15m, 50)[-1]
    except Exception as e:
        snap['errors'].append(f'ema: {e}')

    # ── ATR ──
    try:
        atr4h_vals  = atr(k4h,  14)
        atr15m_vals = atr(k15m, 14)
        snap['atr_4h']  = next(v for v in reversed(atr4h_vals)  if v)
        snap['atr_15m'] = next(v for v in reversed(atr15m_vals) if v)
    except Exception as e:
        snap['errors'].append(f'atr: {e}')

    # ── ADX / DI ──
    try:
        adx4h, dip4h, dim4h = adx_di(k4h, 14)
        snap['adx_4h']    = adx4h[-1]
        snap['di_plus_4h']  = dip4h[-1]
        snap['di_minus_4h'] = dim4h[-1]

        adx1h, dip1h, dim1h = adx_di(k1h, 14)
        snap['adx_1h']    = adx1h[-1]
        snap['di_plus_1h']  = dip1h[-1]
        snap['di_minus_1h'] = dim1h[-1]
    except Exception as e:
        snap['errors'].append(f'adx: {e}')

    # ── Supertrend (approximation) ──
    try:
        snap['supertrend_4h'] = supertrend_approx(k4h,  10, 3.0)
        snap['supertrend_1h'] = supertrend_approx(k1h,  10, 3.0)
    except Exception as e:
        snap['errors'].append(f'supertrend: {e}')

    # ── VWAP (1H session) ──
    try:
        snap['vwap_1h'] = vwap(k1h[-24:])  # 24本分のVWAP
    except Exception as e:
        snap['errors'].append(f'vwap: {e}')

    # ── Volume vs SMA20 ──
    try:
        vsma = vol_sma(k15m, 20)
        cur_vol = float(k15m[-1][5])
        snap['vol_ratio_15m'] = cur_vol / vsma if vsma > 0 else 1.0
    except Exception as e:
        snap['errors'].append(f'volume: {e}')

    # ── RSI ──
    try:
        snap['rsi_1h']  = rsi(_closes(k1h),  14)
        snap['rsi_15m'] = rsi(_closes(k15m), 14)
        snap['rsi_5m']  = rsi(_closes(k5m),  14)
    except Exception as e:
        snap['errors'].append(f'rsi: {e}')

    # ── 15m swing structure (簡易: 直近3本の高値・安値) ──
    try:
        recent = k15m[-6:]
        highs_r = [float(k[2]) for k in recent]
        lows_r  = [float(k[3]) for k in recent]
        snap['swing_higher_high_15m'] = highs_r[-1] > highs_r[-3]
        snap['swing_higher_low_15m']  = lows_r[-1]  > lows_r[-3]
        snap['swing_lower_high_15m']  = highs_r[-1] < highs_r[-3]
        snap['swing_lower_low_15m']   = lows_r[-1]  < lows_r[-3]
    except Exception as e:
        snap['errors'].append(f'swing: {e}')

    # ── Funding rate ──
    try:
        snap['funding_rate'] = _funding_rate(symbol)
    except Exception as e:
        snap['errors'].append(f'funding: {e}')
        snap['funding_rate'] = 0.0

    # ── Spread (bid/ask from ticker) ──
    try:
        t = _ticker_24h(symbol)
        ask=float(t.get('askPrice') or 0); bid=float(t.get('bidPrice') or 0); snap['spread'] = (ask-bid) if ask>0 and bid>0 else snap.get('price',77000)*0.00005
        last = float(t.get('lastPrice') or 0)
        if last > 0:
            snap['price'] = last
        if not snap.get('price') or snap['price'] == 0:
            snap['price'] = float(k5m[-1][4])
    except Exception as e:
        snap['errors'].append(f'ticker: {e}')
        snap['spread'] = 5.0

    # Final price guarantee
    if not snap.get('price') or snap['price'] == 0:
        snap['price'] = float(k5m[-1][4])
    # Final price guarantee
    if not snap.get('price') or snap['price'] == 0:
        snap['price'] = float(k5m[-1][4])
    return snap

# ─────────────────────────────────────────────
# Scoring engine
# ─────────────────────────────────────────────

def compute_scores(s: Dict[str, Any]) -> Tuple[int, int, str]:
    """
    Returns (long_score, short_score, market_mode)
    """
    long_score  = 0
    short_score = 0

    price = s.get('price', 0)

    # ── LONG scoring ──
    if s.get('supertrend_4h') == 'long':
        long_score += 25
    if price and s.get('ema50_4h') and price > s['ema50_4h']:
        long_score += 10
    if s.get('ema50_4h') and s.get('ema200_4h') and s['ema50_4h'] > s['ema200_4h']:
        long_score += 10
    if s.get('supertrend_1h') == 'long':
        long_score += 15
    if price and s.get('ema50_1h') and price > s['ema50_1h']:
        long_score += 10
    if s.get('adx_4h', 0) >= 22 and s.get('di_plus_4h', 0) > s.get('di_minus_4h', 0):
        long_score += 10
    if s.get('swing_higher_high_15m') and s.get('swing_higher_low_15m'):
        long_score += 10
    if price and s.get('vwap_1h') and price > s['vwap_1h']:
        long_score += 5
    if price and s.get('ema20_15m') and price > s['ema20_15m']:
        long_score += 5
    if s.get('vol_ratio_15m', 0) >= 1.2:
        long_score += 10
    if s.get('funding_rate', 0) <= 0.0001:
        long_score += 5

    # ── LONG deductions ──
    if s.get('supertrend_4h') == 'short':
        long_score -= 15
    if s.get('supertrend_1h') == 'short':
        long_score -= 10

    # ── SHORT scoring ──
    if s.get('supertrend_4h') == 'short':
        short_score += 25
    if price and s.get('ema50_4h') and price < s['ema50_4h']:
        short_score += 10
    if s.get('ema50_4h') and s.get('ema200_4h') and s['ema50_4h'] < s['ema200_4h']:
        short_score += 10
    if s.get('supertrend_1h') == 'short':
        short_score += 15
    if price and s.get('ema50_1h') and price < s['ema50_1h']:
        short_score += 10
    if s.get('adx_4h', 0) >= 22 and s.get('di_minus_4h', 0) > s.get('di_plus_4h', 0):
        short_score += 10
    if s.get('swing_lower_high_15m') and s.get('swing_lower_low_15m'):
        short_score += 10
    if price and s.get('vwap_1h') and price < s['vwap_1h']:
        short_score += 5
    if price and s.get('ema20_15m') and price < s['ema20_15m']:
        short_score += 5
    if s.get('vol_ratio_15m', 0) >= 1.2:
        short_score += 10
    if s.get('funding_rate', 0) >= -0.0001:
        short_score += 5

    # ── SHORT deductions ──
    if s.get('supertrend_4h') == 'long':
        short_score -= 15
    if s.get('supertrend_1h') == 'long':
        short_score -= 10

    # ── Clamp 0-100 ──
    long_score  = max(0, min(100, long_score))
    short_score = max(0, min(100, short_score))

    # ── Market mode ──
    adx = s.get('adx_4h', 0)
    st4 = s.get('supertrend_4h', 'long')
    st1 = s.get('supertrend_1h', 'long')

    if adx < 18:
        mode = 'RANGE'
    elif (st4 == 'long'
          and price > s.get('ema50_4h', 0)
          and s.get('ema50_4h', 0) >= s.get('ema200_4h', 0)
          and adx >= 22
          and s.get('di_plus_4h', 0) > s.get('di_minus_4h', 0)):
        mode = 'BULL_TREND'
    elif (st4 == 'short'
          and price < s.get('ema50_4h', 0)
          and s.get('ema50_4h', 0) <= s.get('ema200_4h', 0)
          and adx >= 22
          and s.get('di_minus_4h', 0) > s.get('di_plus_4h', 0)):
        mode = 'BEAR_TREND'
    elif st1 == 'long' and s.get('swing_higher_high_15m') and s.get('swing_higher_low_15m'):
        mode = 'LONG_REVERSAL'
    elif st1 == 'short' and s.get('swing_lower_high_15m') and s.get('swing_lower_low_15m'):
        mode = 'SHORT_REVERSAL'
    else:
        mode = 'RANGE'

    return long_score, short_score, mode

# ─────────────────────────────────────────────
# TP/SL/Size calculator
# ─────────────────────────────────────────────

def calc_trade_params(
    side: str,
    entry_price: float,
    s: Dict[str, Any],
    long_score: int,
    short_score: int,
    account_equity: float = 1132.0,
    mode: str = 'BULL_TREND'
) -> Optional[Dict[str, Any]]:

    score = long_score if side == 'long' else short_score
    adx   = s.get('adx_4h', 20)
    atr4h = s.get('atr_4h', entry_price * 0.01)
    atr15m = s.get('atr_15m', entry_price * 0.002)
    spread = s.get('spread', 5.0)

    # ── RR based on ADX ──
    if adx < 18:   rr = 0.0
    elif adx < 22: rr = 1.75
    elif adx < 35: rr = 2.25
    else:          rr = 3.5

    if mode in ('LONG_REVERSAL', 'SHORT_REVERSAL'):
        rr = 3.5

    if rr == 0:
        return None

    # ── Buffer & stop ──
    buffer = max(entry_price * 0.0005, atr15m * 0.15, spread * 3)

    # ── Swing-based stop ──
    k15m_highs = []
    k15m_lows  = []
    # fallback: ATR-based stop
    if side == 'long':
        stop_loss  = entry_price - atr15m * 1.5 - buffer
    else:
        stop_loss  = entry_price + atr15m * 1.5 + buffer

    stop_width = abs(entry_price - stop_loss)

    # ── Validation ──
    min_stop = max(spread * 3, atr15m * 0.10)
    max_stop = atr4h * 0.75
    if stop_width <= 0 or stop_width < min_stop or stop_width > max_stop:
        return None

    # ── TP ──
    if side == 'long':
        take_profit = entry_price + stop_width * rr
    else:
        take_profit = entry_price - stop_width * rr

    # ── Risk % ──
    if score >= 85:   risk_pct = 0.0035
    elif score >= 75: risk_pct = 0.0025
    elif score >= 70: risk_pct = 0.0020
    else:             risk_pct = 0.0012

    if mode in ('LONG_REVERSAL', 'SHORT_REVERSAL'):
        risk_pct *= 0.5

    risk_usdt = account_equity * risk_pct

    # ── Fee / slippage ──
    entry_fee_rate = 0.0002  # maker
    exit_fee_rate  = 0.0005  # taker SL
    fee_per_btc    = entry_price * (entry_fee_rate + exit_fee_rate)
    slip_per_btc   = spread * 0.5  # maker

    eff_loss = stop_width + fee_per_btc + slip_per_btc
    if eff_loss <= 0:
        return None

    qty_btc = risk_usdt / eff_loss
    qty_btc = round(qty_btc, 3)  # GRVT step size
    qty_btc = max(qty_btc, 0.001)

    notional = qty_btc * entry_price
    eff_lev  = notional / account_equity

    # ── Leverage guard ──
    if eff_lev > 5.0:
        qty_btc  = (account_equity * 5.0) / entry_price
        qty_btc  = round(qty_btc, 3)
        notional = qty_btc * entry_price
        eff_lev  = notional / account_equity

    return {
        'entry_price':        round(entry_price, 1),
        'stop_loss':          round(stop_loss,   1),
        'take_profit':        round(take_profit, 1),
        'rr':                 round(rr, 2),
        'risk_pct':           round(risk_pct, 4),
        'risk_usdt':          round(risk_usdt, 2),
        'qty_btc':            qty_btc,
        'notional_usdt':      round(notional, 2),
        'effective_leverage': round(eff_lev, 2),
    }