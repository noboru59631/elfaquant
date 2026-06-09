# patch_v8_aggressive.py
import pathlib, re

TARGET = pathlib.Path('hft_bot_v8.py')
backup = pathlib.Path('hft_bot_v8_aggressive_backup.py')
backup.write_text(TARGET.read_text(encoding='utf-8'), encoding='utf-8')
print(f'✅ バックアップ作成: {backup}')

text = TARGET.read_text(encoding='utf-8')

# REFRESH_SEC: 0.5 → 0.15（ループ速度3.3倍）
text = re.sub(r'REFRESH_SEC\s*=\s*[\d.]+',
              'REFRESH_SEC     = 0.15', text)

# SPREAD_OFFSET: 現在値 → 0.2（スプレッド極小化、フィル頻度最大化）
text = re.sub(r'SPREAD_OFFSET\s*=\s*Decimal\(["\'][\d.]+["\']\)',
              'SPREAD_OFFSET   = Decimal("0.2")', text)

# REORDER_THRESH: 現在値 → 0.3（価格追従を超高速化）
text = re.sub(r'REORDER_THRESH\s*=\s*Decimal\(["\'][\d.]+["\']\)',
              'REORDER_THRESH  = Decimal("0.3")', text)

# BASE_SIZE と MAX_POSITION は 0.05 のまま維持（リスク管理）
TARGET.write_text(text, encoding='utf-8')

print('✅ aggressive patch 適用完了')
print('   REFRESH_SEC    = 0.15  （旧: 0.5）')
print('   SPREAD_OFFSET  = 0.2   （旧: 0.5）')
print('   REORDER_THRESH = 0.3   （旧: 1.0）')
print('   BASE_SIZE      = 0.05  （変更なし）')
print('   MAX_POSITION   = 0.05  （変更なし）')
print()
print('次のステップ:')
print('  1. 現在のボットを Ctrl+C で停止')
print('  2. python hft_bot_v8.py で再起動')
