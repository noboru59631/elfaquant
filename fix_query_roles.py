with open('elfa_grvt_bot/strategy_engine.py', encoding='utf-8') as f:
    content = f.read()

old_roles = """QUERY_ROLES = {
    'f7667ea4-85f2-4d10-a534-5bf1a67272d3': 'BULL_FILTER_LONG',
    '30d4435d-e933-446f-9162-ca98c4afca03': 'BEAR_FILTER_SHORT',
    'ba66ac38-2d52-457a-b612-b43222e403ff': 'LONG_REVERSAL',
    '6606e987-0f8e-44ea-8343-a9a87466cdf9': 'SHORT_REVERSAL',
    '40f37ee1-92d7-413f-af53-03977830c27b': 'LONG_SETUP_15m',
    'd9067784-75a5-4953-ba9c-29a0cbfee5aa': 'SHORT_SETUP_15m',
    '8abea377-9d40-4728-9514-47dc99a720d9': 'RSI_OVERSOLD',
}"""

new_roles = """QUERY_ROLES = {
    # --- 現行アクティブID (2026-05-23更新) ---
    '726ffdd0-2feb-4111-972b-2a68eae86c7e': 'BULL_FILTER_LONG',    # Q1-BULL_FILTER_LONG
    'da16ab97-d7b9-48a0-8a47-9911cbf9d9ea': 'LONG_REVERSAL',       # Q2-LONG_REVERSAL
    '5e163e96-7dd4-4e2b-a002-5df4a69d7ab7': 'BEAR_FILTER_SHORT',   # BEAR_EMA200_4H
    '511ba089-69b0-4fe7-8388-121e53915070': 'BEAR_FILTER_SHORT',   # BEAR_MOMENTUM_4H
    '2ce7551d-4458-4d4c-b111-1f90d2048ad9': 'BEAR_FILTER_SHORT',   # BEAR_EMA50_1H
    'e1cf734e-4a1c-4fea-9af4-a5c4e5ceebf0': 'BEAR_FILTER_SHORT',   # BEAR_FILTER_SHORT_V2
    'cb038e56-60c8-46a6-a945-a25a19a28a76': 'SHORT_REVERSAL',      # SHORT_REVERSAL_V2
    '55331a30-47a7-44b5-9682-2daaaa1f6f49': 'SHORT_SETUP_15m',     # SHORT_SETUP_15m
    '7050103d-3565-4abb-a37d-8e0ed247bf3f': 'BEAR_FILTER_SHORT',   # BEAR_RSI_CROSS_35
    'f465ad59-5084-4c85-ab2b-10ee330a9720': 'RSI_OVERSOLD',        # BTC RSI Oversold
    'fde37cae-9f2b-487b-9e9f-e0cf4a906958': 'SHORT_SETUP_15m',     # SHORT_INSTANT_1H
    'a98762ab-82cd-4386-bfb0-8a3f4ef2825a': 'SHORT_SETUP_15m',     # SHORT_INSTANT_4H
    'e8f60dd7-9a52-4ec1-97f1-b657d87f9695': 'SHORT_SETUP_15m',     # 追加クエリ
    '9f71f044-0d33-4409-bbaa-2be1545bddb0': 'SHORT_SETUP_15m',     # 追加クエリ
}"""

if old_roles in content:
    content = content.replace(old_roles, new_roles)
    with open('elfa_grvt_bot/strategy_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - QUERY_ROLES updated')
else:
    print('ERROR: pattern not found - trying line replacement')
    # BOMを考慮した別アプローチ
    lines = content.splitlines()
    start = None
    end = None
    for i, l in enumerate(lines):
        if 'QUERY_ROLES = {' in l:
            start = i
        if start is not None and l.strip() == '}' and i > start:
            end = i
            break
    if start is not None and end is not None:
        new_lines = lines[:start] + new_roles.splitlines() + lines[end+1:]
        with open('elfa_grvt_bot/strategy_engine.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines) + '\n')
        print('OK - QUERY_ROLES updated (line method)')
    else:
        print('ERROR: could not find QUERY_ROLES block')

# 確認
with open('elfa_grvt_bot/strategy_engine.py', encoding='utf-8') as f:
    lines = f.readlines()
print('\n=== QUERY_ROLES after update ===')
for i, l in enumerate(lines):
    if i < 22:
        print(f'{i+1:03}: {l.rstrip()}')
