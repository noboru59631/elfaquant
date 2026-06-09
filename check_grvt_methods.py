with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

print('=== GrvtClient 全メソッド一覧 ===')
for i, line in enumerate(lines):
    if line.strip().startswith('def ') or line.strip().startswith('async def '):
        print(f'{i+1:03}: {line.rstrip()}')

print(f'\n合計行数: {len(lines)}')
