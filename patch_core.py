with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

inject = '''
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
                f'Entry={decision.get(\"entry_price\")} SL={decision.get(\"stop_loss\")} TP={decision.get(\"take_profit\")}'
            )
            if action in ('ENTER_LONG', 'ENTER_SHORT'):
                for r in decision.get('reasons', []):
                    self.logger.info(f'[Scoring]   {r}')
                self.logger.info(f'[Scoring] Orders: {decision.get(\"orders\")}')
        except Exception as e:
            self.logger.error(f'[Scoring] Engine error: {e}')

'''

target = '    async def process_fire'
if '_run_scoring_engine' not in content and target in content:
    content = content.replace(target, inject + target)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - core.py patched with scoring engine')
elif '_run_scoring_engine' in content:
    print('OK - already patched')
else:
    print('WARNING - target method not found, showing methods:')
    for i, line in enumerate(content.splitlines()):
        if 'async def' in line:
            print(f'  {i+1}: {line.strip()}')