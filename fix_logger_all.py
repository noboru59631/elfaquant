with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

import re

# self.logger → logging.getLogger(__name__) に全置換
old_count = content.count('self.logger')
content = re.sub(
    r'self\.logger\.',
    'import logging as _lg; _lg = _lg.getLogger(__name__); _lg.',
    content
)

# 上記の置換は冗長なので、よりシンプルな方法で
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

# まず self.logger の使用箇所を確認
lines = content.splitlines()
logger_lines = [(i+1, l) for i, l in enumerate(lines) if 'self.logger' in l]
print(f'self.logger 使用箇所: {len(logger_lines)}件')
for ln, l in logger_lines[:5]:
    print(f'  {ln:03}: {l.strip()}')

# __init__ に logger を追加する
if 'self.logger = ' not in content:
    # __init__ メソッドを見つけてlogger初期化を追加
    old_init = 'def __init__(self'
    # Core クラスの __init__ を探す
    init_pos = content.find('class Core')
    if init_pos == -1:
        init_pos = 0
    init_in_class = content.find('def __init__(self', init_pos)
    
    if init_in_class != -1:
        # __init__ の最初の行末を見つける
        init_line_end = content.find('\n', init_in_class)
        # bodyの開始（次の行）
        body_start = init_line_end + 1
        # インデントを検出
        next_line = content[body_start:content.find('\n', body_start)]
        indent = len(next_line) - len(next_line.lstrip())
        indent_str = ' ' * indent
        
        # super().__init__() の後か、最初のself.の前にlogger追加
        logger_init = f'{indent_str}import logging as _logging\n{indent_str}self.logger = _logging.getLogger(__name__)\n'
        
        # docstringがある場合はその後に追加
        body_content = content[body_start:]
        # 最初の self. の位置に挿入
        first_self = body_content.find(f'{indent_str}self.')
        if first_self != -1:
            insert_pos = body_start + first_self
            content = content[:insert_pos] + logger_init + content[insert_pos:]
            print('OK - self.logger added to __init__')
        else:
            print('WARN - could not find insertion point')
    else:
        print('WARN - __init__ not found')
else:
    print('OK - self.logger already initialized')

with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 確認
with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

# __init__ 周辺を表示
print('\n=== Core.__init__ (最初の20行) ===')
in_init = False
count = 0
for i, line in enumerate(lines):
    if 'class Core' in line:
        in_init = True
    if in_init:
        print(f'{i+1:03}: {line.rstrip()}')
        count += 1
        if count > 25:
            break
