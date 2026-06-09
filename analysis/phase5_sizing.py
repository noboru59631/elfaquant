"""
Phase 5: SL/TP price and position-sizing calculator.

Takes the phase4 entry decision plus live price/balance/ATR and produces a
concrete SL price, TP price and position size (in BTC, GRVT-tradable
0.001 BTC increments).
"""
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Optional

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
sys.path.insert(0, str(THIS_DIR))

from phase1_regime import detect_regime
from phase2_fundamentals import analyze_fundamentals
from phase3_technical import analyze_technical
from phase4_entry import evaluate_entry

SL_ATR_MULTIPLIER = 1.5
TP_ATR_MULTIPLIER = 3.0
RR_RATIO          = TP_ATR_MULTIPLIER / SL_ATR_MULTIPLIER  # 1:2

MIN_SIZE_BTC      = 0.001   # GRVT minimum tradable increment
MAX_SIZE_FRACTION = 0.1     # balance/price * 0.1 -> ~10x leverage equivalent at 10% of equity

REGIME_RISK_ADJUSTMENT = {
    'HIGH_VOL':   0.5,
    'TREND_UP':   1.0,
    'TREND_DOWN': 1.0,
    'RANGE':      0.8,
}


def _floor_to_step(value: float, step: float) -> float:
    return math.floor(value / step + 1e-9) * step


def calculate_sizing(
    entry_result: Dict[str, Any],
    price: float,
    balance: float,
    atr: float,
    risk_pct: float = 0.01,
) -> Dict[str, Any]:
    decision = entry_result.get('decision', 'HOLD')
    regime   = entry_result.get('regime')

    sl_distance = atr * SL_ATR_MULTIPLIER
    tp_distance = atr * TP_ATR_MULTIPLIER

    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    if decision == 'ENTER_LONG':
        sl_price = price - sl_distance
        tp_price = price + tp_distance
    elif decision == 'ENTER_SHORT':
        sl_price = price + sl_distance
        tp_price = price - tp_distance

    risk_amount = balance * risk_pct

    size = 0.0
    if decision in ('ENTER_LONG', 'ENTER_SHORT') and sl_distance > 0:
        raw_size = risk_amount / sl_distance

        adjustment = REGIME_RISK_ADJUSTMENT.get(regime, 1.0)
        adjusted_size = raw_size * adjustment

        max_size = (balance / price) * MAX_SIZE_FRACTION
        capped_size = min(adjusted_size, max_size)

        # Floor to GRVT's 0.001 BTC step last, so the final size that gets
        # quoted/traded is always a valid tradable increment.
        size = round(_floor_to_step(capped_size, MIN_SIZE_BTC), 3)
        if size == 0.0 and balance >= 10.0:
            size = MIN_SIZE_BTC
            print("[SIZING] min_size guaranteed: 0.001 BTC")

    return {
        'decision':    decision,
        'entry_price': price,
        'sl_price':    round(sl_price, 1) if sl_price is not None else None,
        'tp_price':    round(tp_price, 1) if tp_price is not None else None,
        'size':        size,
        'risk_amount': round(risk_amount, 2),
        'rr_ratio':    RR_RATIO,
        'atr':         atr,
    }


if __name__ == '__main__':
    phase1 = detect_regime()
    phase2 = analyze_fundamentals()
    phase3 = analyze_technical()
    phase4 = evaluate_entry(phase1, phase2, phase3)

    price = phase3['price']      # live mid/reference price (last 4H close)
    atr   = phase1['atr']        # daily ATR, passed through from phase1

    sizing = calculate_sizing(phase4, price=price, balance=700.0, atr=atr)

    print(json.dumps({
        'phase4_entry':  phase4,
        'phase5_sizing': sizing,
    }, indent=2, ensure_ascii=False))
