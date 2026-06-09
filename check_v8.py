import pathlib, re
TARGET = pathlib.Path('hft_bot_v8.py')
text = TARGET.read_text(encoding='utf-8')
if 'MM Bot v7' in text:
    print('❌ v7コードが混入しています')
else:
    print('✅ v8コードです')
for param in ['REFRESH_SEC', 'SPREAD_OFFSET', 'REORDER_THRESH', 'BASE_SIZE', 'MAX_POSITION', 'DAILY_LOSS_LIMIT']:
    match = re.search(rf'{param}\s*=\s*[^\n]+', text)
    if match:
        print(f'   {match.group()}')
    else:
        print(f'   {param}: 見つかりません')
