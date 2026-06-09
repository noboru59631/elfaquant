with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

# スプレッドの上限を0.03%に変更 (0.2% → 0.03%)
content = content.replace(
    "return max(SPREAD_MIN, min(vol_spread, 0.002))  # 最大0.2%",
    "return max(SPREAD_MIN, min(vol_spread, 0.0003))  # 最大0.03%"
)

# SPREAD_ALPHAを小さく (2.0 → 0.3)
content = content.replace(
    "SPREAD_ALPHA   = 2.0         # ATR感度係数",
    "SPREAD_ALPHA   = 0.3         # ATR感度係数"
)

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('修正完了')
