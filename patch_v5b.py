with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

# BID/ASK価格計算を修正: 常にベスト板の内側1tickを使用
old = """            my_bid = round(best_bid + 0.1 - skew, 1)
            my_ask = round(best_ask - 0.1 - skew, 1)
            if my_ask <= my_bid:
                my_bid = round(mid - half, 1)
                my_ask = round(mid + half, 1)"""

new = """            # 常にベスト板の内側1tickに配置 (スプレッド保証付き)
            my_bid = round(best_bid + 0.1 - skew, 1)
            my_ask = round(best_ask - 0.1 - skew, 1)
            # スプレッドが潰れた場合のみフォールバック
            min_gap = round(mid * 0.0002, 1)  # 最小0.02%
            if my_ask - my_bid < min_gap:
                my_bid = round(mid - min_gap / 2, 1)
                my_ask = round(mid + min_gap / 2, 1)"""

content = content.replace(old, new)
with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('修正完了' if old in open('mm_bot.py').read() == False else '修正失敗')
