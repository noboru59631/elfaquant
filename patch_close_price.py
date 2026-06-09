with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

old = '                    close_price = round(mid * (1 - 0.0001) if is_closing_buy else mid * (1 + 0.0001), 1)'
new = '                    # ショートクローズ(Buy): best_bid+0.1 / ロングクローズ(Sell): best_ask-0.1\n                    close_price = round(best_bid + 0.1 if is_closing_buy else best_ask - 0.1, 1)'

if old in content:
    content = content.replace(old, new)
    print("close_price修正完了")
else:
    print("パターンが見つかりません")

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
