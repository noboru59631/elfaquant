with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    content = f.read()

# _client → client に修正
old = 'r = await self._client.post(url, json={"instrument": symbol}, timeout=10)'
new = 'r = await self.client.post(url, json={"instrument": symbol}, timeout=10)'

if old in content:
    content = content.replace(old, new)
    with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - _client → client fixed in tick_size')
else:
    print('ERROR: pattern not found')

# 確認
with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== tick_size method ===')
in_method = False
for i, line in enumerate(lines):
    if 'async def tick_size' in line:
        in_method = True
    if in_method:
        print(f'{i+1:03}: {line.rstrip()}')
    if in_method and i > 0 and line.strip() == '' and i > 5:
        # 2行空行で終了
        break
