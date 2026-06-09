with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

old = '''            if remote_status in TERMINAL_STATUSES:
                # sync_terminal_status disabled to prevent infinite loop
                pass  # sync_terminal_status disabled
                return'''

new = '''            if remote_status in TERMINAL_STATUSES:
                if remote_status == 'triggered':
                    # Query was triggered: mark fired locally and exit loop
                    # Supervisor will NOT reset this one - just log and exit
                    self.registry.update_strategy_status(query_id, 'fired')
                    import logging as _log
                    _log.getLogger(__name__).info(
                        f'[Loop] {query_id[:8]} triggered remotely - exiting loop (no auto-order)')
                    return
                else:
                    # expired / cancelled / failed
                    self.registry.update_strategy_status(query_id, remote_status)
                    return'''

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - triggered_loop fixed')
else:
    print('ERROR: pattern not found')
    for i, line in enumerate(content.splitlines()[88:100], start=89):
        print(f'{i:03}: {repr(line)}')
