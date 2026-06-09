with open('elfa_grvt_bot/grvt_client.py', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'if sl_price:' in l:
        start = i
        print(f"Found at line {i+1}: {l.rstrip()}")
        for j in range(i, min(i+15, len(lines))):
            print(f"{j+1:03}: {lines[j].rstrip()}")
        break
