with open('mm_bot_v7.py', encoding='utf-8') as f:
    content = f.read()

old = '''async def cancel_all(grvt: GrvtClient) -> None:
    if CFG.dry_run: return
    try:
        headers = {"Cookie": grvt.cookie,
                   "X-Grvt-Account-Id": grvt.account_id}
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post("https://trades.grvt.io/full/v1/cancel_all_orders",
                         headers=headers,
                         json={"sub_account_id": grvt.account_id,
                               "kind": ["PERPETUAL"],
                               "base": ["BTC"], "quote": ["USDT"]})
    except Exception as e:
        print(f"  [cancel error] {e}")'''

new = '''async def cancel_all(grvt: GrvtClient) -> None:
    if CFG.dry_run: return
    try:
        from mm_bot_v6 import cancel_all as cancel_all_v6
        await cancel_all_v6(grvt)
    except Exception as e:
        print(f"  [cancel error] {e}")'''

content = content.replace(old, new)

with open('mm_bot_v7.py', 'w', encoding='utf-8') as f:
    f.write(content)

if 'cancel_all_v6' in content:
    print("✅ cancel_all修正完了")
else:
    print("❌ 修正失敗 — 手動確認が必要")
