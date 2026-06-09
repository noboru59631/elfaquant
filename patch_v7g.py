# patch_v7g.py — 自動再起動 + SIZE縮小パッチ
with open('mm_bot_v7.py', encoding='utf-8') as f:
    content = f.read()

original = content

# ===== 修正1: SIZE 0.02 → 0.01 =====
old1 = 'size_btc        : Decimal = Decimal("0.02")'
new1 = 'size_btc        : Decimal = Decimal("0.01")'
# バリエーション違いも対応
old1b = "size_btc        : Decimal = Decimal('0.02')"
new1b = "size_btc        : Decimal = Decimal('0.01')"

# ===== 修正2: MAX_POS 0.04 → 0.02 =====
old2 = 'max_pos_btc     : Decimal = Decimal("0.04")'
new2 = 'max_pos_btc     : Decimal = Decimal("0.02")'
old2b = "max_pos_btc     : Decimal = Decimal('0.04')"
new2b = "max_pos_btc     : Decimal = Decimal('0.02')"

# ===== 修正3: asyncio.run(main()) を run_forever() に置換 =====
old3 = 'asyncio.run(main())'
new3 = '''async def run_forever():
    """日次損失上限到達後30分待機して自動再起動。累計-$100で完全停止。"""
    import datetime
    cumulative_loss = Decimal("0")
    CUMULATIVE_LIMIT = Decimal("-100")
    COOLDOWN_MIN = 30

    session = 0
    while True:
        session += 1
        print(f"\\n{'='*55}")
        print(f"  🚀 セッション #{session} 開始  "
              f"({datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC)")
        print(f"  累計損益: ${float(cumulative_loss):+.2f}  "
              f"(上限: ${float(CUMULATIVE_LIMIT):.0f})")
        print(f"{'='*55}")

        # セッション開始前残高を取得して損益計算に使う
        try:
            import pathlib, json
            env = {k.strip(): v.strip()
                   for line in pathlib.Path('.env').read_text(encoding='utf-8').splitlines()
                   if '=' in line and not line.startswith('#')
                   for k, v in [line.split('=', 1)]}
            from elfa_grvt_bot.grvt_client import GrvtClient
            _grvt_tmp = GrvtClient(
                api_key=env['GRVT_TRADING_API_KEY'],
                private_key=env['GRVT_TRADING_PRIVATE_KEY'])
            await _grvt_tmp.login()
            _acct = await get_account(_grvt_tmp)
            bal_before = Decimal(str(_acct.get("total_equity", 0)))
            await _grvt_tmp.close()
        except Exception as e:
            print(f"  ⚠️  残高取得失敗: {e}")
            bal_before = Decimal("0")

        # main() 実行
        try:
            await main()
        except Exception as e:
            print(f"  ❌ セッション例外: {e}")

        # セッション終了後残高を取得して損益を計算
        try:
            _grvt_tmp2 = GrvtClient(
                api_key=env['GRVT_TRADING_API_KEY'],
                private_key=env['GRVT_TRADING_PRIVATE_KEY'])
            await _grvt_tmp2.login()
            _acct2 = await get_account(_grvt_tmp2)
            bal_after = Decimal(str(_acct2.get("total_equity", 0)))
            await _grvt_tmp2.close()
            session_pnl = bal_after - bal_before
            cumulative_loss += session_pnl
            print(f"\\n  📊 セッション #{session} 終了")
            print(f"     損益: ${float(session_pnl):+.2f}  "
                  f"累計: ${float(cumulative_loss):+.2f}")
        except Exception as e:
            print(f"  ⚠️  終了残高取得失敗: {e}")

        # 累計損失チェック
        if cumulative_loss <= CUMULATIVE_LIMIT:
            print(f"\\n🚨 累計損失 ${float(cumulative_loss):+.2f} が"
                  f" ${float(CUMULATIVE_LIMIT):.0f} を超えました。")
            print("   ボットを完全停止します。")
            break

        # 30分クールダウン
        print(f"\\n  ⏳ {COOLDOWN_MIN}分後に再起動します... "
              f"(Ctrl+C で完全停止)")
        print(f"     再起動予定: "
              f"{(datetime.datetime.utcnow() + datetime.timedelta(minutes=COOLDOWN_MIN)).strftime('%H:%M:%S')} UTC")
        try:
            for remaining in range(COOLDOWN_MIN * 60, 0, -30):
                mins, secs = divmod(remaining, 60)
                print(f"     残り {mins:02d}:{secs:02d}", end='\\r')
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            print("\\n  ⏹ クールダウン中に停止シグナル受信")
            break
        print()  # 改行

    print("\\n✅ run_forever() 終了")

asyncio.run(run_forever())'''

# 適用
applied = []

# SIZE
for old, new in [(old1, new1), (old1b, new1b)]:
    if old in content:
        content = content.replace(old, new)
        applied.append('SIZE 0.02→0.01')
        break

# MAX_POS
for old, new in [(old2, new2), (old2b, new2b)]:
    if old in content:
        content = content.replace(old, new)
        applied.append('MAX_POS 0.04→0.02')
        break

# run_forever
if old3 in content:
    content = content.replace(old3, new3)
    applied.append('run_forever() 追加')

# 書き込み
if len(applied) > 0:
    with open('mm_bot_v7.py', 'w', encoding='utf-8') as f:
        f.write(content)
    for item in applied:
        print(f'✅ {item}')
    print(f'\n適用済み: {len(applied)}/3')
    if len(applied) < 3:
        print('⚠️  一部未適用 → 手動確認が必要')
else:
    print('❌ 何も変更されませんでした（変数名が異なる可能性あり）')
    print('\n--- SIZE関連行を検索 ---')
    for i, line in enumerate(original.splitlines()):
        if 'size_btc' in line or 'max_pos' in line.lower():
            print(f'{i+1:4d}: {line}')
