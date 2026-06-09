import httpx
import json
import os
import sys

# .envを読み込む
with open('.env', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

api_key = os.environ.get('ELFA_API_KEY', '')
if not api_key:
    print('ERROR: ELFA_API_KEY not found')
    sys.exit(1)

# Step1: まずValidate
payload = {
    "query": {
        "conditions": {
            "AND": [
                {
                    "source": "ta",
                    "method": "rsi",
                    "args": {"symbol": "BTC", "timeframe": "1h"},
                    "operator": "<",
                    "value": 30
                }
            ]
        },
        "actions": [
            {
                "stepId": "step_1",
                "type": "notify",
                "params": {"message": "BTC RSI oversold - enter long"}
            }
        ],
        "expiresIn": "3d"
    },
    "title": "BTC RSI Oversold",
    "description": "BTC 1h RSI below 30 long entry"
}

headers = {"x-elfa-api-key": api_key, "Content-Type": "application/json"}

print("=== Validating query ===")
r = httpx.post("https://api.elfa.ai/v2/auto/queries/validate", json=payload, headers=headers, timeout=30)
print(f"Status: {r.status_code}")
print(r.text[:500])

if r.status_code == 200:
    print("\n=== Creating query on Elfa API ===")
    r2 = httpx.post("https://api.elfa.ai/v2/auto/queries", json=payload, headers=headers, timeout=30)
    print(f"Status: {r2.status_code}")
    print(r2.text)
    if r2.status_code in (200, 201):
        data = r2.json()
        print(f"\nSUCCESS! Elfa query_id = {data.get('queryId', data)}")
else:
    print("\nValidation failed - check the error above")