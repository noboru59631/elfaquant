# patch_v7q.py  ── ASKオフセットを強制修正 + ポジション解消優先モード
import pathlib, re

path = pathlib.Path("mm_bot_v7.py")
code = path.read_text(encoding="utf-8")

# calc_quotes関数を確認するため表示
lines = code.splitlines()
for i, line in enumerate(lines, 1):
    if 'calc_quotes' in line or 'calc_spread' in line or 'bid_px' in line or 'ask_px' in line:
        print(f"L{i}: {line}")
