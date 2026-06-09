# patch_v7r.py  ── skew_maxを安全な値に縮小
import pathlib, re

path = pathlib.Path("mm_bot_v7.py")
code = path.read_text(encoding="utf-8")

# skew_maxを8.0→1.0に縮小（half=3.0より必ず小さい値）
old = 'skew_max        : Decimal = Decimal("8.0")    # 最大スキュー USD'
new = 'skew_max        : Decimal = Decimal("1.0")    # 最大スキュー USD'

if old in code:
    code = code.replace(old, new)
    path.write_text(code, encoding="utf-8")
    print("✅ patch_v7r 適用完了：skew_max 8.0 → 1.0")
else:
    print("❌ 対象箇所が見つかりません")
    for i, line in enumerate(code.splitlines()[15:20], start=16):
        print(f"L{i}: {repr(line)}")
