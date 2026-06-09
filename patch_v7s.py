# patch_v7s.py（修正版）
import re, shutil, pathlib

SRC = pathlib.Path("mm_bot_v7.py")
shutil.copy(SRC, SRC.with_suffix(".py.bak_v7s"))

txt = SRC.read_text(encoding="utf-8")

# skew_max: Decimal("1.0") → Decimal("3.0")
txt, n1 = re.subn(
    r'(skew_max\s*.*?Decimal\(")1\.0(")',
    r'\g<1>3.0\2',
    txt
)

# daily_loss_limit: Decimal("-15") → Decimal("-20")
txt, n2 = re.subn(
    r'(daily_loss_limit\s*.*?Decimal\(")(-15)(")',
    r'\g<1>-20\3',
    txt
)

SRC.write_text(txt, encoding="utf-8")

print(f"✅ patch_v7s 適用完了")
print(f"   skew_max       : 1.0 → 3.0   ({n1}箇所)")
print(f"   daily_loss_limit: -15 → -20  ({n2}箇所)")
