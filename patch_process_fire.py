import re

with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# Already patched?
if '_run_scoring_engine' in content and 'await self._run_scoring_engine' in content:
    print('Already patched - skipping')
    exit(0)

# Target: replace step 8 place order block with scoring-first version
old_step8 = '''        # 8. Place order
        try:
            result = await self.grvt.place_entry_with_tpsl(
                symbol=strategy['symbol'],
                entry_side=strategy['side'],
                amount=strategy['amount'],
                order_type=strategy['order_type'],
                limit_price=strategy.get('price'),
                time_in_force=strategy.get('time_in_force', 'GTC'),
                reference_price=mid,
                tp_price=tp_price,
                sl_price=sl_price
            )
'''

new_step8 = '''        # 8. Run scoring while order params override from engine
        try:
            from .strategy_engine import evaluate as _engine_eval
            decision = _engine_eval(query_id, account_equity=1132.0)
            action = decision.get('action', 'HOLD')
            ls = decision.get('long_score', 0)
            ss = decision.get('short_score', 0)
            mode = decision.get('mode', 'RANGE')
            self.logger.info(f'[Scoring] action={action} mode={mode} L={ls} S={ss}')
            for reason in decision.get('reasons', []):
                self.logger.info(f'[Scoring]   {reason}')
            if action == 'HOLD':
                await self.registry.update_fire_outcome(event_id, 'hold_scoring', f'HOLD: L={ls} S={ss} mode={mode}')
                await self.alerts.emit('info', 'scoring_hold',
                    f'Scoring HOLD: L={ls} S={ss} mode={mode}',
                    query_id=query_id, fire_event_id=event_id)
                return
            # Override order params from scoring engine
            if decision.get('entry_price'):
                mid = decision.get('entry_price')
            if decision.get('stop_loss'):
                sl_price = decision.get('stop_loss')
            if decision.get('take_profit'):
                tp_price = decision.get('take_profit')
            if decision.get('qty_btc'):
                strategy['amount'] = decision.get('qty_btc')
            if decision.get('effective_leverage'):
                strategy['leverage'] = min(int(decision['effective_leverage']), 5)
            if action == 'ENTER_LONG':
                strategy['side'] = 'buy'
            elif action == 'ENTER_SHORT':
                strategy['side'] = 'sell'
            strategy['order_type'] = 'market'
        except Exception as _score_err:
            self.logger.warning(f'[Scoring] Error (using strategy defaults): {_score_err}')

        # 8. Place order
        try:
            result = await self.grvt.place_entry_with_tpsl(
                symbol=strategy['symbol'],
                entry_side=strategy['side'],
                amount=strategy['amount'],
                order_type=strategy['order_type'],
                limi]_price=strategy.get('price'),
                time_in_force=strategy.get('time_in_force', 'GTC'),
                reference_price=mid,
                tp_price=tp_price,
                sl_price=sl_price
            )
'''

if old_step8 in content:
    content = content.replace(old_step8, new_step8)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - process_fire patched with scoring engine integration')
else:
    print('WARNING - old block not found, showing lines 220-240:')
    lines = content.splitlines()
    for i, l in enumerate(lines[219:240], 220):
        print(f'{i}: {l}')
