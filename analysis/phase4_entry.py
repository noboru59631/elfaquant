"""
Phase 4: Entry decision - integrates phase1 (regime), phase2 (fundamentals)
and phase3 (technical) results into a single ENTER_LONG / ENTER_SHORT / HOLD
decision.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
sys.path.insert(0, str(THIS_DIR))

from phase1_regime import detect_regime
from phase2_fundamentals import analyze_fundamentals
from phase3_technical import analyze_technical

LONG_TREND_THRESHOLD  = 3.0
SHORT_TREND_THRESHOLD = -3.0
LONG_RANGE_THRESHOLD  = 4.0
SHORT_RANGE_THRESHOLD = -4.0


def evaluate_entry(phase1: Dict[str, Any], phase2: Dict[str, Any], phase3: Dict[str, Any]) -> Dict[str, Any]:
    """Combine the three phase results into an entry decision.

    total_score = macro_score*0.2 + phase2_score*0.4 + phase3_score*0.4
    """
    regime       = phase1.get('regime')
    macro_score  = phase1.get('macro_score', 0)
    phase2_score = phase2.get('phase2_score', 0)
    phase3_score = phase3.get('phase3_score', 0)

    total_score = macro_score * 0.2 + phase2_score * 0.4 + phase3_score * 0.4

    if regime == 'HIGH_VOL':
        decision = 'HOLD'
        reason = f'regime=HIGH_VOL -> forced HOLD (total_score={total_score:.2f})'
    elif regime == 'TREND_UP' and total_score >= LONG_TREND_THRESHOLD:
        decision = 'ENTER_LONG'
        reason = f'regime=TREND_UP and total_score={total_score:.2f} >= {LONG_TREND_THRESHOLD}'
    elif regime == 'TREND_DOWN' and total_score <= SHORT_TREND_THRESHOLD:
        decision = 'ENTER_SHORT'
        reason = f'regime=TREND_DOWN and total_score={total_score:.2f} <= {SHORT_TREND_THRESHOLD}'
    elif regime == 'RANGE' and total_score >= LONG_RANGE_THRESHOLD:
        decision = 'ENTER_LONG'
        reason = f'regime=RANGE and total_score={total_score:.2f} >= {LONG_RANGE_THRESHOLD}'
    elif regime == 'RANGE' and total_score <= SHORT_RANGE_THRESHOLD:
        decision = 'ENTER_SHORT'
        reason = f'regime=RANGE and total_score={total_score:.2f} <= {SHORT_RANGE_THRESHOLD}'
    else:
        decision = 'HOLD'
        reason = f'no entry condition met (regime={regime}, total_score={total_score:.2f})'

    return {
        'decision':     decision,
        'total_score':  round(total_score, 3),
        'macro_score':  macro_score,
        'phase2_score': phase2_score,
        'phase3_score': phase3_score,
        'regime':       regime,
        'reason':       reason,
    }


if __name__ == '__main__':
    phase1 = detect_regime()
    phase2 = analyze_fundamentals()
    phase3 = analyze_technical()
    decision = evaluate_entry(phase1, phase2, phase3)

    print(json.dumps({
        'phase1_regime':       phase1,
        'phase2_fundamentals': phase2,
        'phase3_technical':    phase3,
        'phase4_entry':        decision,
    }, indent=2, ensure_ascii=False))
