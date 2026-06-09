with open('mm_bot.py', encoding='utf-8') as f:
    content = f.read()

old = '''    except KeyboardInterrupt:
        print("\\n⏹ 手動停止")

    await cancel_all(grvt)
    data = await get_account_data(grvt)
    end_balance = float(data.get("total_equity", 0))

    print("\\n" + "=" * 65)
    print(f"  開始残高: ${start_balance:,.2f} → 終了残高: ${end_balance:,.2f}")
    print(f"  純損益  : ${end_balance - start_balance:+,.4f}")
    print(f"  累計出来高: ${total_volume:,.0f}")
    print(f"  フィル: {total_fills}回 (BID:{bid_fills} ASK:{ask_fills} 成行クローズ:{market_closes})")
    print("=" * 65)
    await grvt.close()'''

new = '''    except KeyboardInterrupt:
        print("\\n⏹ 手動停止 — 注文キャンセル＆ポジションクローズ中...")

    finally:
        # 🛡️ 正常停止・強制停止どちらでも必ず実行
        await cancel_all(grvt)
        print("  ✅ 全注文キャンセル完了")

        # ポジションが残っていれば成行クローズ
        acct_end = await get_account_data(grvt)
        pos_list_end = acct_end.get("open_positions", [])
        if pos_list_end:
            final_pos = Decimal(str(pos_list_end[0]["size"]))
            if abs(final_pos) >= Decimal("0.01"):
                print(f"  ⚠️ ポジション残存: {float(final_pos):+.3f} BTC → 成行クローズ実行")
                is_closing_buy = final_pos < 0
                await place_market_close(grvt, is_closing_buy, abs(final_pos))
                print("  ✅ ポジション成行クローズ完了")
        else:
            print("  ✅ ポジションなし — 安全に停止")

        data = await get_account_data(grvt)
        end_balance = float(data.get("total_equity", 0))

        print("\\n" + "=" * 65)
        print(f"  開始残高: ${start_balance:,.2f} → 終了残高: ${end_balance:,.2f}")
        print(f"  純損益  : ${end_balance - start_balance:+,.4f}")
        print(f"  累計出来高: ${total_volume:,.0f}")
        print(f"  フィル: {total_fills}回 (BID:{bid_fills} ASK:{ask_fills} 成行クローズ:{market_closes})")
        print("=" * 65)
        await grvt.close()'''

if old in content:
    content = content.replace(old, new)
    with open('mm_bot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 修正完了")
else:
    print("❌ 対象コードが見つかりません — 手動確認が必要")
