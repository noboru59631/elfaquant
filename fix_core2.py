with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# 壊れた部分を正しいtry/exceptに修正
old = '''            state = await self.elfa.get_query(query_id)
            except Exception as e:
                if getattr(e, 'status_code', None) == 404:
                    await self.registry.update_strategy_status(query_id, 'failed')
                    await self.alerts.emit('error', 'strategy_terminated_remotely',
                                          f'strategy not found on Elfa', query_id=query_id)
                    return
                raise'''

new = '''            try:
                state = await self.elfa.get_query(query_id)
            except Exception as e:
                if getattr(e, 'status_code', None) == 404:
                    await self.registry.update_strategy_status(query_id, 'failed')
                    await self.alerts.emit('error', 'strategy_terminated_remotely',
                                          f'strategy not found on Elfa', query_id=query_id)
                    return
                import asyncio as _a
                await _a.sleep(15)
                continue'''

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - fixed')
else:
    print('ERROR: pattern not found, showing lines 65-80:')
    for i, line in enumerate(content.splitlines()[64:80], start=65):
        print(f'{i:03}: {repr(line)}')
