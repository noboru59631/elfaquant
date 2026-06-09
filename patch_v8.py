"""
patch_v8.py
hft_bot_v8.py の MAX_POSITION を 0.10 → 0.05 に更新するパッチ
"""
import pathlib
import re

TARGET = pathlib.Path("hft_bot_v8.py")

if not TARGET.exists():
    print(f"❌ {TARGET} が見つかりません。")
    print("   hft_bot_v8.py と同じフォルダで実行してください。")
    exit(1)

# バックアップ作成
backup = pathlib.Path("hft_bot_v8_backup.py")
backup.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
print(f"✅ バックアップ作成: {backup}")

# 置換
original = TARGET.read_text(encoding="utf-8")
updated  = re.sub(
    r'MAX_POSITION\s*=\s*Decimal\("0\.10"\)',
    'MAX_POSITION   = Decimal("0.05")  # BASE_SIZEと同じ：ナンピン完全排除',
    original
)

if original == updated:
    print("⚠️  置換対象が見つかりませんでした。")
    print("   すでに 0.05 になっているか、記述形式が異なる可能性があります。")
else:
    TARGET.write_text(updated, encoding="utf-8")
    print("✅ patch_v8 適用完了：MAX_POSITION を 0.05 に更新しました")

# 確認表示
for i, line in enumerate(TARGET.read_text(encoding="utf-8").splitlines(), 1):
    if "MAX_POSITION" in line or "BASE_SIZE" in line:
        print(f"   [{i:03d}] {line.strip()}")
