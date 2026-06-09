import re

with open('elfa_grvt_bot/core.py', encoding='utf-8') as f:
    content = f.read()

old = '''    async def strategy_loop(self, query_id: str):'''

new = '''    async def strategy_loop(self, query_id: str):
        import httpx as _httpx'''

# すでにパッチ済みかチェック
if 'ConnectTimeout' in content:
    print('Already patched')
else:
    old2 = '            state = await self.elfa.get_query(query_id)'
    new2 = '''            try:
                state = await self.elfa.get_query(query_id)
            except Exception as _e:
                import logging
                logging.getLogger(__name__).warning(f'[strategy_loop] retrying {query_id[:8]} after: {_e}')
                await asyncio.sleep(15)
                continue'''

    content = content.replace(old2, new2)

    with open('elfa_grvt_bot/core.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - timeout retry patch applied')
