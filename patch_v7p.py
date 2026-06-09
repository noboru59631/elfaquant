# patch_v7p.py  ── BID/ASKサイズを在庫上限でクランプ
import re, pathlib

path = pathlib.Path("mm_bot_v7.py")
code = path.read_text(encoding="utf-8")

old = (
    "            bid_ok = ask_ok = False\n"
    "            if quote_bid and position < CFG.max_inv:\n"
    "                bid_ok = await place_limit(grvt, True,  bid_px, size)\n"
    "            if quote_ask and position > -CFG.max_inv:\n"
    "                ask_ok = await place_limit(grvt, False, ask_px, size)"
)

new = (
    "            bid_ok = ask_ok = False\n"
    "            if quote_bid and position < CFG.max_inv:\n"
    "                bid_size = min(size, CFG.max_inv - position)\n"
    "                bid_size = (bid_size / Decimal('0.001')).to_integral_value() * Decimal('0.001')\n"
    "                if bid_size >= Decimal('0.001'):\n"
    "                    bid_ok = await place_limit(grvt, True,  bid_px, bid_size)\n"
    "            if quote_ask and position > -CFG.max_inv:\n"
    "                ask_size = min(size, CFG.max_inv + position)\n"
    "                ask_size = (ask_size / Decimal('0.001')).to_integral_value() * Decimal('0.001')\n"
    "                if ask_size >= Decimal('0.001'):\n"
    "                    ask_ok = await place_limit(grvt, False, ask_px, ask_size)"
)

if old in code:
    code = code.replace(old, new)
    path.write_text(code, encoding="utf-8")
    print("✅ patch_v7p 適用完了：BID/ASKサイズをmax_invでクランプ")
else:
    print("❌ 対象箇所が見つかりません。コードを確認してください")
    # デバッグ用：L302〜L306を表示
    for i, line in enumerate(code.splitlines()[301:307], start=302):
        print(f"L{i}: {repr(line)}")
