import pathlib, re
text = pathlib.Path('mm_bot_v7.py').read_text(encoding='utf-8')
print("=== v7で使用しているURL ===")
urls = re.findall(r'https?://[^\s\'"]+', text)
for u in sorted(set(urls)):
    print(f"  {u}")
print("\n=== .envのキー名 ===")
env_keys = re.findall(r'os\.getenv\(["\']([^"\']+)["\']', text)
for k in sorted(set(env_keys)):
    print(f"  {k}")
print("\n=== ログイン関数 ===")
lines = text.splitlines()
for i, line in enumerate(lines):
    if any(x in line.lower() for x in ['def login', 'def _login', 'async def login']):
        for l in lines[i:i+20]:
            print(f"  {l}")
        print()
