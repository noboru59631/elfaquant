with open('mm_bot_v7.py', encoding='utf-8') as f:
    content = f.read()

# get_account関数をmm_bot_v6と同じ方式に置き換え
old = '''async def get_account(grvt: GrvtClient) -> dict:
    headers = {"Cookie": grvt.cookie,
               "X-Grvt-Account-Id": grvt.account_id}
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post("https://trades.grvt.io/full/v1/account_summary",
                         headers=headers, json={})
    return r.json().get("result", {})'''

new = '''async def get_account(grvt: GrvtClient) -> dict:
    from mm_bot_v6 import get_account_data
    return await get_account_data(grvt)'''

content = content.replace(old, new)

with open('mm_bot_v7.py', 'w', encoding='utf-8') as f:
    f.write(content)

if 'get_account_data' in content:
    print("✅ get_account修正完了")
else:
    print("❌ 修正失敗")
