with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

old = '''            if lonely_since and time.time() - lonely_since > LONELY_SEC:
                if abs(position) >= Decimal("0.01"):
                    elapsed = int(time.time() - lonely_since)
                    print(f"\\n  ⏰ [{lonely_side}のみ約定 {elapsed}秒経過] "
                          f"ポジ:{float(position):+.3f}BTC → 段階クローズ開始")
                    await cancel_all(grvt)
                    await place_market_close(grvt, position)
                    market_closes += 1
                    taker_cost = float(abs(position)) * mid * TAKER_FEE
                    daily_pnl -= taker_cost
                    print(f"  テイカー手数料: -${taker_cost:.3f}")
                lonely_since = None
                lonely_side  = None
                await asyncio.sleep(1)
                continue'''

new = '''            if lonely_since and time.time() - lonely_since > LONELY_SEC:
                if abs(position) >= Decimal("0.01"):
                    elapsed = int(time.time() - lonely_since)
                    print(f"\\n  [MAKER_CLOSE] [{lonely_side}のみ約定 {elapsed}秒経過] "
                          f"ポジ:{float(position):+.3f}BTC → Maker指値クローズ試行")
                    await cancel_all(grvt)
                    # Maker指値でクローズ (post_only=True)
                    is_closing_buy = position < 0
                    close_price = round(mid * (1 - 0.0001) if is_closing_buy else mid * (1 + 0.0001), 1)
                    close_result = await grvt._place_single_order(
                        symbol=SYMBOL,
                        is_buying=is_closing_buy,
                        amount=abs(position),
                        is_market=False,
                        limit_price=Decimal(str(close_price)),
                        time_in_force="GTT",
                        reduce_only=True,
                        post_only=True,
                    )
                    maker_close_id = close_result.get("client_order_id", "")
                    print(f"  Maker指値クローズ注文: {'OK' if maker_close_id else 'NG'} @ ${close_price:,.1f}")
                    # MAKER_TIMEOUT秒待機してフィル確認
                    await asyncio.sleep(MAKER_CLOSE_TIMEOUT)
                    # ポジション再取得
                    bal2, pos2 = await get_account(grvt)
                    if abs(pos2) >= Decimal("0.01"):
                        # まだ残っていればTakerで強制クローズ
                        print(f"  Maker未フィル → Takerで強制クローズ (残:{float(pos2):+.3f}BTC)")
                        await cancel_all(grvt)
                        await place_market_close(grvt, pos2)
                        market_closes += 1
                        taker_cost = float(abs(pos2)) * mid * TAKER_FEE
                        daily_pnl -= taker_cost
                        print(f"  Taker手数料: -${taker_cost:.3f}")
                    else:
                        print(f"  Makerクローズ成功! リベート獲得")
                        maker_rebate = float(abs(position)) * mid * MAKER_REBATE
                        daily_pnl += maker_rebate
                lonely_since = None
                lonely_side  = None
                await asyncio.sleep(1)
                continue'''

if old in content:
    content = content.replace(old, new)
    print("クローズロジック修正完了")
else:
    print("パターンが見つかりません")

with open('mm_bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
