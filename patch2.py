with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    content = f.read()

# 重複している post_only を削除 (191行目付近の _place_single_order のみ残す)
# _sign_order の方に誤って追加された post_only を除去
old = '''    async def _sign_order(
        self,
        sub_account_id: str,
        client_order_id: int,
        time_in_force_int: int,
        instrument: str,
        size_str: str,
        limit_price_str: str,
        is_buying: bool,
        nonce: int,
        expiration_ns: str,
        is_market: bool,
        reduce_only: bool,
        post_only: bool = False,
    )'''

new = '''    async def _sign_order(
        self,
        sub_account_id: str,
        client_order_id: int,
        time_in_force_int: int,
        instrument: str,
        size_str: str,
        limit_price_str: str,
        is_buying: bool,
        nonce: int,
        expiration_ns: str,
        is_market: bool,
        reduce_only: bool,
    )'''

if old in content:
    content = content.replace(old, new)
    print('_sign_order の重複 post_only を除去しました')
else:
    print('パターンが見つかりません — 手動確認が必要')

with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
