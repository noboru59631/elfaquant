with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

old = '''            # Fill detection
            acct     = await get_account_data(grvt)
            pos_list = acct.get("open_positions", [])
            new_pos  = (Decimal(str(pos_list[0]["size"]))
                        if pos_list else Decimal("0"))

            if new_pos != position:
                diff = new_pos - position
                side = "BID" if diff > 0 else "ASK"
                await on_fill(side, mid, abs(diff), True)'''

new = '''            # Fill detection
            acct     = await get_account_data(grvt)
            pos_list = acct.get("positions", [])

            # Find BTC_USDT_Perp position
            new_pos = Decimal("0")
            for p in pos_list:
                if p.get("instrument") == SYMBOL:
                    raw = Decimal(str(p["size"]))
                    # Positive = long, negative = short
                    new_pos = raw
                    break

            if new_pos != position:
                diff = new_pos - position
                side = "BID" if diff > 0 else "ASK"
                fill_price = mid
                print(f"  💰 [{'BID' if diff>0 else 'ASK'}フィル] "
                      f"{'+'if diff>0 else ''}{float(diff):.3f}BTC"
                      f" @ ${float(fill_price):,.1f}"
                      f"  Pos:{float(new_pos):+.3f}BTC")
                await on_fill(side, fill_price, abs(diff), True)'''

content = content.replace(old, new)

with open('mm_bot_v6.py', 'w', encoding='utf-8') as f:
    f.write(content)

if 'p.get("instrument") == SYMBOL' in content:
    print("✅ フィル検知修正完了")
else:
    print("❌ 修正失敗")
