with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()

init_end = -1
for i, l in enumerate(lines):
    if 'self.alerts = alerts' in l:
        init_end = i
        break

in_init = False
if init_end != -1:
    for i, l in enumerate(lines):
        if 'def __init__' in l:
            for j in range(i, min(i+15, len(lines))):
                if '_last_fired' in lines[j]:
                    in_init = True
            break

if in_init:
    print("already fixed")
elif init_end == -1:
    print("ERROR: pattern not found")
else:
    lines.insert(init_end + 1, "        self._cooldown_sec: int = 4 * 3600\n")
    lines.insert(init_end + 1, "        self._last_fired: dict = {}\n")
    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"OK - inserted at line {init_end+2}")

with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'def __init__' in l:
        for j in range(i, min(i+14, len(lines))):
            print(f"{j+1:03}: {lines[j].rstrip()}")
        break
