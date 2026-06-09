with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '"GTC":               ("GOOD_TILL_TIME"' in l:
        lines.insert(i, '            "GTT":               ("GOOD_TILL_TIME",      1),\n')
        print(f'GTT マッピングを {i+1} 行目に追加しました')
        break

with open('elfa_grvt_bot/grvt_client.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
