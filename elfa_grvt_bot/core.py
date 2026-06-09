import asyncio
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, AsyncGenerator
from datetime import datetime

@dataclass
class Reject:
    reason: str

@dataclass
class Allow:
    pass

class Core:
    """
    Implements the core algorithms for the Elfa GRVT bot.
    """
    
    def __init__(self, registry, elfa_client, grvt_client, alerts):
        import logging as _logging
        self.logger = _logging.getLogger(__name__)
        self.registry = registry
        self.elfa = elfa_client
        self.grvt = grvt_client
        self.alerts = alerts
        self._last_fired: dict = {}
        self._cooldown_sec: int = 4 * 3600
        
    async def supervisor(self):
        """
        Main supervisor loop that manages all strategy tasks.
        """
        tasks = {}
        POLL_INTERVAL_S = 5.0
        
        while True:
            # Auto-reset fired strategies back to active
            # DISABLED: import sqlite3 as _sq
            # DISABLED: _c = _sq.connect('registry.db')
            # DISABLED: _fired = _c.execute("SELECT count(*) FROM strategies WHERE status='fired'").fetchone()[0]
            # DISABLED: if _fired > 0:
            # DISABLED: _c.execute("UPDATE strategies SET status='active' WHERE status='fired'")
            # DISABLED: _c.commit()
            # DISABLED: import logging as _log
            # DISABLED: _log.getLogger(__name__).info(f'[Supervisor] Auto-reset {_fired} fired strategies to active')
            # DISABLED: _c.close()

            active = self.registry.list_strategies(status='active')
            active_ids = {s['query_id'] for s in active}
            
            # Spawn missing tasks
            for s in active:
                if s['query_id'] not in tasks or tasks[s['query_id']].done():
                    tasks[s['query_id']] = asyncio.create_task(
                        self.strategy_loop(s['query_id'])
                    )
            
            # Reap tasks for strategies no longer active
            for qid in list(tasks.keys()):
                if qid not in active_ids:
                    tasks[qid].cancel()
                    del tasks[qid]
            
            # Reap exited tasks
            for qid, t in list(tasks.items()):
                if t.done():
                    del tasks[qid]
            
            await asyncio.sleep(POLL_INTERVAL_S)
    
    async def strategy_loop(self, query_id: str):
        """
        Manages a single strategy's lifecycle.
        """
        BACKOFF_INITIAL_S = 2.0
        BACKOFF_MAX_S = 60.0
        backoff = BACKOFF_INITIAL_S
        TERMINAL_STATUSES = {'triggered', 'expired', 'cancelled', 'failed'}
        
        while True:
            # 1. Status reconciliation
            try:
                state = await self.elfa.get_query(query_id)
            except Exception as e:
                if getattr(e, 'status_code', None) == 404:
                    self.registry.update_strategy_status(query_id, 'failed')
                    await self.alerts.emit('error', 'strategy_terminated_remotely', 
                                          f'strategy not found on Elfa', query_id=query_id)
                    return
                await asyncio.sleep(15)
                continue
            
            remote_status = state['status']
            executions = state.get('executions', []) or []
            
            if remote_status in TERMINAL_STATUSES:
                if remote_status == 'triggered':
                    # Query triggered: place order then exit
                    import logging as _lg; _lg.getLogger(__name__).info(f'[Loop] {query_id[:8]} triggered - processing order')
                    fake_event_id = f'poll_{query_id[:8]}'
                    await self.process_fire(fake_event_id, query_id, {})
                    self.registry.update_strategy_status(query_id, 'fired')
                    return
                else:
                    # expired / cancelled / failed
                    self.registry.update_strategy_status(query_id, remote_status)
                    return
                
            if remote_status == 'recurring':
                self.registry.update_strategy_status(query_id, 'failed')
                await self.alerts.emit('error', 'strategy_terminated_remotely',
                                      'recurring queries are not supported', query_id=query_id)
                return
                
            # Check for missed executions
            for ex in executions:
                # fire_exists replaced with always-process
                if True:
                    self.registry.add_fire(
                        event_id=ex['id'], query_id=query_id,
                        outcome='unknown', raw_payload=json.dumps(ex)
                    )
                    await self.alerts.emit('error', 'manual_intervention_required',
                        'strategy triggered while receiver was offline',
                        query_id=query_id, fire_event_id=ex['id'],
                        details={'execution': ex})
            
            # 2. Process SSE stream
            try:
                async for event in self.elfa.stream_notifications(query_id):
                    await self.process_fire(
                        event['event_id'], query_id, event['data'])
                    return
                
                backoff = BACKOFF_INITIAL_S
                
            except Exception as e:
                status_code = getattr(e, 'status_code', None)
                if status_code in (401, 404):
                    await self.alerts.emit('error', 'strategy_terminated_remotely',
                                          f'SSE failed: HTTP {status_code}', query_id=query_id)
                    self.registry.update_strategy_status(query_id, 'failed')
                    return
                
                # Exponential backoff for transient errors
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX_S)
    

    async def _run_scoring_engine(self, query_id: str) -> None:
        try:
            from .strategy_engine import evaluate as engine_evaluate
            decision = engine_evaluate(query_id, account_equity=1132.0)
            action = decision.get('action', 'HOLD')
            ls = decision.get('long_score', 0)
            ss = decision.get('short_score', 0)
            mode = decision.get('mode', 'RANGE')
            self.logger.info(
                f'[Scoring] {action} | Mode={mode} L={ls} S={ss} | '
                f'Entry={decision.get("entry_price")} SL={decision.get("stop_loss")} TP={decision.get("take_profit")}'
            )
            if action in ('ENTER_LONG', 'ENTER_SHORT'):
                for r in decision.get('reasons', []):
                    self.logger.info(f'[Scoring]   {r}')
                self.logger.info(f'[Scoring] Orders: {decision.get("orders")}')
        except Exception as e:
            self.logger.error(f'[Scoring] Engine error: {e}')

    async def process_fire(self, event_id: str, query_id: str, raw_payload: dict):
        """
        Process a trigger event from Elfa.
        """
        # 1. Dedupe
        try:
            self.registry.add_fire(
                event_id=event_id, query_id=query_id,
                outcome='unknown', raw_payload=json.dumps(raw_payload)
            )
        except Exception:
            return  # duplicate event
            
        # 2. Get strategy
        # ── クールダウンチェック ──────────────────────────
        import time as _time
        now_ts = _time.time()
        last = self._last_fired.get(query_id, 0)
        elapsed = now_ts - last
        if elapsed < self._cooldown_sec:
            remaining = int(self._cooldown_sec - elapsed)
            self.logger.info(
                f"[Cooldown] {query_id[:8]} skipped - "
                f"{remaining//3600}h{(remaining%3600)//60}m remaining"
            )
            return
        # ─────────────────────────────────────────────────

        strategy = self.registry.get_strategy(query_id)
        if not strategy:
            self.registry.update_fire_outcome(event_id, 'unknown_strategy',
                                                  'no local strategy for this query_id')
            await self.alerts.emit('warning', 'unknown_strategy',
                                 f'SSE fire for unknown strategy {query_id}',
                                 query_id=query_id, fire_event_id=event_id)
            return
        
        # 3. Alert trigger received
        await self.alerts.emit('info', 'trigger_received',
            f'Elfa trigger fired: {strategy["title"]}. '
            f'Placing {strategy["side"].upper()} {strategy["amount"]} {strategy["symbol"]} '
            f'({strategy["order_type"]}) on GRVT',
            query_id=query_id, fire_event_id=event_id)
        
        # 4. Fetch reference price
        try:
            mid = await self.grvt.fetch_mid_price(strategy['symbol'])
        except Exception as e:
            await self.finalize_failure(
                event_id, query_id, 'grvt_error', 'grvt_other',
                f'fetch_mid_price failed: {e}')
            return
        
        # 5. Check guardrails
        guard = self.check_guardrails(strategy, mid)
        if isinstance(guard, Reject):
            self.registry.update_fire_outcome(
                event_id, 'rejected_guardrail', guard.reason)
            self.registry.update_strategy_status(query_id, 'fired')
            await self.alerts.emit('warning', 'guardrail_rejected',
                                 f'fire rejected: {guard.reason}',
                                 query_id=query_id, fire_event_id=event_id)
            return
        
        # 6. Set leverage if specified
        if strategy.get('leverage') is not None:
            try:
                await self.grvt.set_leverage(
                    symbol=strategy['symbol'], 
                    leverage=strategy['leverage'])
            except Exception as e:
                await self.alerts.emit('warning', 'grvt_set_leverage',
                                     f'set_leverage failed: {e}',
                                     query_id=query_id, fire_event_id=event_id)
        
        # 7. Compute TP/SL prices
        tp_price = sl_price = None
        if strategy.get('tp_pct') is not None:
            tp_price = self.align_tick(
                self.compute_target_price(
                    mid, strategy['tp_pct'], strategy['side'], kind='tp'),
                tick_size=await self.grvt.tick_size(strategy['symbol']),
                direction='down' if strategy['side'] == 'buy' else 'up'
            )
        if strategy.get('sl_pct') is not None:
            sl_price = self.align_tick(
                self.compute_target_price(
                    mid, strategy['sl_pct'], strategy['side'], kind='sl'),
                tick_size=await self.grvt.tick_size(strategy['symbol']),
                direction='up' if strategy['side'] == 'buy' else 'down'
            )
        
        # 8. Run scoring while order params override from engine
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
                self.registry.update_fire_outcome(event_id, 'hold_scoring', f'HOLD: L={ls} S={ss} mode={mode}')
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
            # Ensure authenticated before placing order
            if not self.grvt.cookie:
                login_ok = await self.grvt.login()
                if not login_ok:
                    await self.finalize_failure(
                        event_id, query_id, 'grvt_error', 'grvt_auth_failed',
                        'GRVT login() returned False')
                    return
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
            
            # 9. Record success
            import time as _time
            self._last_fired[query_id] = _time.time()
            self.registry.update_fire_outcome(
                event_id,
                outcome='placed',
                parent_order_id=result['parent_order_id'],
                tp_order_id=result.get('tp_order_id'),
                sl_order_id=result.get('sl_order_id'),
                reference_price=mid,
                tp_price=tp_price,
                sl_price=sl_price
            )
            self.registry.update_strategy_status(query_id, 'fired')
            await self.alerts.emit('info', 'order_placed',
                f'{strategy["side"].upper()} {strategy["amount"]} {strategy["symbol"]} '
                f'({strategy["order_type"]}) placed on GRVT',
                query_id=query_id, fire_event_id=event_id)
                
        except Exception as e:
            category = 'grvt_auth_failed' if 'authenticate' in str(e).lower() else 'grvt_other'
            await self.finalize_failure(
                event_id, query_id, 'grvt_error', category,
                f'order placement failed: {e}')
    
    async def finalize_failure(self, event_id, query_id, outcome, category, message):
        """Handle failed order placement."""
        self.registry.update_fire_outcome(event_id, outcome, error=message)
        self.registry.update_strategy_status(query_id, 'fired')
        await self.alerts.emit('error', category, message,
                             query_id=query_id, fire_event_id=event_id)
    
    async def sync_terminal_status(self, query_id, remote_status, executions):
        """Sync terminal status from Elfa to local registry."""
        LOCAL_STATUS = {
            'triggered': 'fired', 'expired': 'expired',
            'cancelled': 'cancelled', 'failed': 'failed'
        }
        new_status = LOCAL_STATUS.get(remote_status, 'failed')
        self.registry.update_strategy_status(query_id, new_status)
        
        if remote_status == 'triggered':
            for ex in executions:
                # fire_exists replaced with always-process
                if True:
                    self.registry.add_fire(
                        event_id=ex['id'], query_id=query_id,
                        outcome='unknown', raw_payload=json.dumps(ex)
                    )
                    await self.alerts.emit('error', 'manual_intervention_required',
                        'strategy triggered while receiver was offline',
                        query_id=query_id, fire_event_id=ex['id'],
                        details={'execution': ex})
            return
        
        SEVERITY = {'expired': 'info', 'cancelled': 'warning', 'failed': 'error'}
        await self.alerts.emit(SEVERITY[remote_status], 'strategy_terminated_remotely',
                            f'strategy ended with status {remote_status!r}',
                            query_id=query_id, details={'executions': executions[:10]})
    
    def check_guardrails(self, strategy, reference_price) -> Reject | Allow:
        """Check strategy guardrails."""
        # Convert inputs to Decimal
        amount = Decimal(str(strategy['amount']))
        max_notional = Decimal(str(strategy['max_notional_usd']))
        ref_price = Decimal(str(reference_price))
        
        # 1. Notional cap
        notional = amount * ref_price
        if notional > max_notional:
            return Reject(
                f'notional ${float(notional):.2f} exceeds max ${float(max_notional):.2f}')
                
        # 2. Environment check
        if strategy.get('env') != 'prod':
            return Reject(f'strategy env is {strategy["env"]!r}, expected prod')
            
        # 3. Amount sanity
        if amount <= 0:
            return Reject(f'amount {float(amount)} must be positive')
            
        return Allow()
    
    def compute_target_price(self, reference, pct, entry_side, kind):
        """Compute TP or SL price from reference and percentage."""
        pct_frac = pct / 100.0
        if entry_side == 'buy':
            if kind == 'tp': return float(reference) * (1 + pct_frac)
            if kind == 'sl': return float(reference) * (1 - pct_frac)
        if entry_side == 'sell':
            if kind == 'tp': return float(reference) * (1 - pct_frac)
            if kind == 'sl': return float(reference) * (1 + pct_frac)
        raise ValueError(f"bad inputs: entry_side={entry_side}, kind={kind}")
    
    def align_tick(self, price, tick_size, direction):
        """Round price to nearest tick."""
        from decimal import Decimal, ROUND_DOWN, ROUND_UP, ROUND_HALF_EVEN
        p = Decimal(str(price))
        t = Decimal(str(tick_size))
        mode = {'down': ROUND_DOWN, 'up': ROUND_UP, 'nearest': ROUND_HALF_EVEN}[direction]
        aligned = (p / t).quantize(Decimal('1'), rounding=mode) * t
        return float(aligned)