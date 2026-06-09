with open('mm_bot_v6.py', encoding='utf-8') as f:
    content = f.read()

# Fix 1: main()のGrvtClient初期化を修正
old = '''    grvt = await GrvtClient.create(
        env["GRVT_API_KEY"],
        env["GRVT_SUB_ACCOUNT_ID"],
        "https://trades.grvt.io",
    )'''

new = '''    grvt = GrvtClient(
        api_key=env["GRVT_TRADING_API_KEY"],
        private_key=env["GRVT_TRADING_PRIVATE_KEY"],
    )
    await grvt.login()'''

content = content.replace(old, new)

# Fix 2: get_mid_priceをfetch_mid_priceに変更
old2 = '''    mid = await get_mid_price(grvt)
            if mid == 0:
                print("  [WARN] mid price取得失敗 — スキップ")
                await asyncio.sleep(REFRESH_SEC)
                continue'''

new2 = '''    mid = Decimal(str(await grvt.fetch_mid_price(SYMBOL)))
            if mid == 0:
                print("  [WARN] mid price取得失敗 — スキップ")
                await asyncio.sleep(REFRESH_SEC)
                continue'''

content = content.replace(old2, new2)

with open('mm_bot_v6.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 確認
if 'GRVT_TRADING_API_KEY' in content and 'fetch_mid_price' in content:
    print("✅ 修正完了")
else:
    print("❌ 修正失敗")
