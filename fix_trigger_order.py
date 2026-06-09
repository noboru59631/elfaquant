with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

old_block = (
    '            if remote_status in TERMINAL_STATUSES:\n'
    '                if remote_status == \'triggered\':\n'
    '                    # Query was triggered: mark fired locally and exit loop\n'
    '                    # Supervisor will NOT reset this one - just log and exit\n'
    '                    self.registry.update_strategy_status(query_id, \'fired\')\n'
    '                    import logging as _log\n'
    '                    _log.getLogger(__name__).info(\n'
    '                        f\'[Loop] {query_id[:8]} triggered remotely - exiting loop (no auto-order)\')\n'
    '                    return\n'
    '                else:\n'
    '                    # expired / cancelled / failed\n'
    '                    self.registry.update_strategy_status(query_id, remote_status)\n'
    '                    return\n'
)

new_block = (
    '            if remote_status in TERMINAL_STATUSES:\n'
    '                if remote_status == \'triggered\':\n'
    '                    # Query triggered: place order then exit\n'
    '                    self.logger.info(f\'[Loop] {query_id[:8]} triggered - processing order\')\n'
    '                    fake_event_id = f\'poll_{query_id[:8]}\'\n'
    '                    await self.process_fire(fake_event_id, query_id, {})\n'
    '                    self.registry.update_strategy_status(query_id, \'fired\')\n'
    '                    return\n'
    '                else:\n'
    '                    # expired / cancelled / failed\n'
    '                    self.registry.update_strategy_status(query_id, remote_status)\n'
    '                    return\n'
)

content = ''.join(lines)
if old_block in content:
    content = content.replace(old_block, new_block)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - trigger order fix applied')
else:
    print('ERROR: pattern not found')
    for i, line in enumerate(lines[93:107], start=94):
        print(f'{i:03}: {repr(line)}')
