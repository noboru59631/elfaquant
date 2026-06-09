"""fix_login_parse.py - login()のaccount_idパースを修正"""

with open("elfa_grvt_bot/grvt_client.py", encoding="utf-8") as f:
    content = f.read()

# login()のaccount_id取得部分を修正
old = '''            data = r.json()
            self.account_id = str(
                data.get("result", {}).get("account_id")
                or data.get("account_id")
                or data.get("result", {}).get("sub_account_id")
                or ""
            )'''

new = '''            data = r.json()
            # レスポンス構造: {"status":"success","sub_account_id":"7643292000705847",...}
            self.account_id = str(
                data.get("sub_account_id")
                or data.get("account_id")
                or data.get("result", {}).get("sub_account_id")
                or data.get("result", {}).get("account_id")
                or ""
            )'''

if old in content:
    content = content.replace(old, new)
    with open("elfa_grvt_bot/grvt_client.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("OK - login() account_id parse fixed")
else:
    print("ERROR: pattern not found, applying line-based fix...")
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'or data.get("result", {}).get("sub_account_id")' in line:
            # その行の前後を含むブロックを置換
            print(f"  Found at line {i+1}: {line.rstrip()}")
    # 強制置換: login()内のself.account_id代入を書き換え
    import re
    pattern = r'self\.account_id = str\([^)]+\)'
    replacement = '''self.account_id = str(
                data.get("sub_account_id")
                or data.get("account_id")
                or data.get("result", {}).get("sub_account_id")
                or ""
            )'''
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count > 0:
        with open("elfa_grvt_bot/grvt_client.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"OK - regex fix applied ({count} replacements)")
    else:
        print("ERROR: regex fix also failed")

# 確認: login()部分を表示
with open("elfa_grvt_bot/grvt_client.py", encoding="utf-8") as f:
    lines = f.readlines()

print("\n=== login() method (lines 29-60) ===")
for i in range(28, min(60, len(lines))):
    print(f"{i+1:03}: {lines[i].rstrip()}")
