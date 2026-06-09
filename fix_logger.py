with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

old = "                    self.logger.info(f'[Loop] {query_id[:8]} triggered - processing order')"
new = "                    import logging as _lg; _lg.getLogger(__name__).info(f'[Loop] {query_id[:8]} triggered - processing order')"

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - logger fixed')
else:
    print('ERROR: pattern not found')
    with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
        lines = f.readlines()
    for i in range(93, 103):
        print(f'{i+1:03}: {repr(lines[i])}')
