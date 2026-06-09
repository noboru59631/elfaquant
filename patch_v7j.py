# patch_v7j.py  cooldown_until global宣言追加
TARGET = 'mm_bot_v7.py'

OLD = '    global position, entry_price, entry_time, daily_pnl\n    global total_vol, maker_fills, start_balance, rolling_pnl'
NEW = '    global position, entry_price, entry_time, daily_pnl\n    global total_vol, maker_fills, start_balance, rolling_pnl\n    global cooldown_until'

with open(TARGET, encoding='utf-8') as f:
    src = f.read()

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(src)
    print('✅ cooldown_until global宣言追加完了')
else:
    print('❌ 対象箇所が見つかりません')
