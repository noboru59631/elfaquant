"""
Integrated runner: executes Phase1 (regime) -> Phase2 (fundamentals) ->
Phase3 (technical) -> Phase4 (entry decision) -> Phase5 (SL/TP/sizing) and
prints a human-readable summary to the console.
"""
import sys
from pathlib import Path
from typing import Any, Dict

# Windows console defaults to cp932, which can't encode the emoji used below.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
sys.path.insert(0, str(THIS_DIR))

from phase1_regime import detect_regime
from phase2_fundamentals import analyze_fundamentals
from phase3_technical import analyze_technical
from phase4_entry import evaluate_entry
from phase5_sizing import calculate_sizing

VERDICT_EMOJI = {'BULLISH': '🟢', 'BEARISH': '🔴', 'NEUTRAL': '⚪'}
REGIME_EMOJI = {
    'TREND_UP': '📈 TREND_UP',
    'TREND_DOWN': '📉 TREND_DOWN',
    'RANGE': '↔️  RANGE',
    'HIGH_VOL': '⚡ HIGH_VOL',
}


def _to_trading_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    return symbol if symbol.endswith('USDT') else f'{symbol}USDT'


def run_analysis(symbol: str = 'BTC', balance: float = 700.0) -> Dict[str, Any]:
    trading_symbol = _to_trading_symbol(symbol)

    phase1 = detect_regime(trading_symbol)
    phase2 = analyze_fundamentals(trading_symbol)
    phase3 = analyze_technical(trading_symbol)
    phase4 = evaluate_entry(phase1, phase2, phase3)

    price = phase3.get('price')
    atr = phase1.get('atr')
    if phase4['decision'] in ('ENTER_LONG', 'ENTER_SHORT') and price is not None and atr is not None:
        phase5 = calculate_sizing(phase4, price=price, balance=balance, atr=atr)
    else:
        phase5 = calculate_sizing(phase4, price=price or 0.0, balance=balance, atr=atr or 0.0)

    return {
        'symbol': symbol,
        'trading_symbol': trading_symbol,
        'balance': balance,
        'phase1': phase1,
        'phase2': phase2,
        'phase3': phase3,
        'phase4': phase4,
        'phase5': phase5,
    }


def _print_summary(result: Dict[str, Any]) -> None:
    symbol = result['symbol']
    phase1, phase2, phase3, phase4, phase5 = (
        result['phase1'], result['phase2'], result['phase3'], result['phase4'], result['phase5']
    )

    print('=' * 60)
    print(f'📊 {symbol} トレード分析サマリー')
    print('=' * 60)

    print(f"\n[Phase1] 🌐 レジーム: {REGIME_EMOJI.get(phase1.get('regime'), phase1.get('regime'))}")
    print(f"   EMA20/50/200: {phase1.get('ema20'):.1f} / {phase1.get('ema50'):.1f} / {phase1.get('ema200'):.1f}")
    print(f"   ATR: {phase1.get('atr'):.1f} (30日平均: {phase1.get('atr_avg30'):.1f})")

    p2_emoji = VERDICT_EMOJI.get(phase2.get('verdict'), '⚪')
    print(f"\n[Phase2] 💰 ファンダメンタルズ: {p2_emoji} {phase2.get('verdict')} (score: {phase2.get('phase2_score')})")
    print(f"   funding_rate: {phase2.get('funding_rate'):.6f} | OI変化率: {phase2.get('oi_change_pct')}% | 24h値動き: {phase2.get('price_change_pct')}%")

    p3_emoji = VERDICT_EMOJI.get(phase3.get('verdict'), '⚪')
    print(f"\n[Phase3] 📐 テクニカル: {p3_emoji} {phase3.get('verdict')} (score: {phase3.get('phase3_score')})")
    print(f"   trend={phase3.get('group_a')} momentum={phase3.get('group_b')} "
          f"price_level={phase3.get('group_c')} volume={phase3.get('group_d')}")
    print(f"   現在価格: {phase3.get('price'):.1f}")

    print(f"\n[Phase4] 🎯 エントリー判定: {phase4.get('decision')}")
    print(f"   total_score: {phase4.get('total_score')} ({phase4.get('reason')})")

    print('\n' + '-' * 60)
    decision = phase4.get('decision')
    if decision == 'HOLD':
        print('⏸️  エントリーなし (HOLD)')
    else:
        side_emoji = '🟢 ロング' if decision == 'ENTER_LONG' else '🔴 ショート'
        print(f'🚀 {side_emoji}エントリー ({decision})')
        print(f"   Entry価格 : {phase5.get('entry_price'):.1f}")
        print(f"   🛑 SL価格 : {phase5.get('sl_price')}")
        print(f"   🎯 TP価格 : {phase5.get('tp_price')}  (RR 1:{phase5.get('rr_ratio')})")
        print(f"   📦 サイズ : {phase5.get('size')} BTC")
        print(f"   💸 リスク額: ${phase5.get('risk_amount')} (balance={result['balance']})")
    print('-' * 60)


if __name__ == '__main__':
    result = run_analysis(symbol='BTC', balance=700.0)
    _print_summary(result)
