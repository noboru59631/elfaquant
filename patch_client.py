import re

with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    content = f.read()

# 1) reduce_only の後に post_only パラメータを追加
content = content.replace(
    '        reduce_only: bool = False,\n    ) -> Dict:',
    '        reduce_only: bool = False,\n        post_only: bool = False,\n    ) -> Dict:'
)

# 2) order_payload 内の post_only を変数に (最初の1箇所のみ)
content = content.replace(
    '"post_only":      False,',
    '"post_only":      post_only,',
    1
)

with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('修正完了')
