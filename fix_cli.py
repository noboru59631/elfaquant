with open('elfa_grvt_bot/cli.py', encoding='utf-8') as f:
    content = f.read()

import json

old = "            eql = parse_eql_input(args.eql)"
new = "            eql_raw = parse_eql_input(args.eql)\n            eql = json.dumps(eql_raw) if isinstance(eql_raw, dict) else eql_raw"

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/cli.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - patched')
else:
    print('Pattern not found, showing context:')
    for i, line in enumerate(content.splitlines()):
        if 'parse_eql_input' in line:
            print(f'{i+1}: {repr(line)}')