# patch_v7i.py  T3後クールダウンパッチ
TARGET = 'mm_bot_v7.py'

OLD = '                quote_bid = quote_ask = False\n\n            elif tier == 4:'
NEW = '                quote_bid = quote_ask = False\n                # T3後クールダウン（5分間新規注文停止）\n                cooldown_until = time.time() + CFG.cooldown_sec\n                print(f"  ❄️  T3クールダウン開始 ({CFG.cooldown_sec}秒)")\n\n            elif tier == 4:'

with open(TARGET, encoding='utf-8') as f:
    src = f.read()

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(src)
    print("✅ T3クールダウン追加完了 (line 283付近)")
else:
    print("❌ 対象箇所が見つかりません。手動確認が必要です")
