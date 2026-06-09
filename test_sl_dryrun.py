"""
Dry-run test for the SL (stop-loss) trigger order path in GrvtClient.place_entry_with_tpsl.

Does NOT hit the network or GRVT's prod API (this bot is prod-only / real money).
Instead it monkeypatches GrvtClient.client.post to capture the outgoing payloads,
so we can verify that:
  - _sign_order is called with the correct keyword arguments (no TypeError)
  - self.client.post is used (not the nonexistent self._client)
  - the SL trigger payload is well-formed and signed
"""
import asyncio
import secrets

from eth_account import Account


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


async def main():
    from elfa_grvt_bot.grvt_client import GrvtClient

    # Throwaway key - only used to exercise the EIP-712 signing path locally.
    fake_private_key = '0x' + secrets.token_hex(32)
    fake_signer = Account.from_key(fake_private_key).address

    grvt = GrvtClient(api_key='dryrun', private_key=fake_private_key)
    # Skip login() (network); fake the auth state it would normally populate.
    grvt.cookie = 'dryrun-cookie'
    grvt.account_id = '123456789'

    captured_calls = []

    async def fake_post(url, json=None, **kwargs):
        captured_calls.append({'url': url, 'payload': json, 'kwargs': kwargs})
        order = json['order']
        return FakeResponse(200, {
            'result': {
                'order_id': f"0xFAKE-{order['metadata']['client_order_id'][-6:]}",
                'state': {'status': 'PENDING'},
            }
        })

    grvt.client.post = fake_post  # monkeypatch - no real HTTP

    result = await grvt.place_entry_with_tpsl(
        symbol='BTC_USDT_Perp',
        entry_side='buy',
        amount=0.001,
        order_type='market',
        limit_price=None,
        time_in_force='GTC',
        reference_price=65000.0,
        tp_price=None,       # isolate the SL path
        sl_price=64000.0,
    )

    print(f'place_entry_with_tpsl result: {result}')
    print(f'Captured {len(captured_calls)} outbound order POST(s)')

    sl_calls = [
        c for c in captured_calls
        if c['payload']['order'].get('trigger', {}).get('trigger_type') == 'STOP_LOSS'
    ]
    assert len(sl_calls) == 1, f'expected exactly 1 SL trigger order, got {len(sl_calls)}'
    sl_order = sl_calls[0]['payload']['order']

    # --- Structural checks -------------------------------------------------
    sig = sl_order['signature']
    for field in ('signer', 'r', 's', 'v', 'expiration', 'nonce', 'chain_id'):
        assert field in sig, f'signature missing field {field!r}: {sig}'
    assert sig['signer'].lower() == fake_signer.lower(), 'signature signer mismatch'
    assert sig['chain_id'] == '325'

    leg = sl_order['legs'][0]
    assert leg['instrument'] == 'BTC_USDT_Perp'
    # entry_side='buy' (long) -> SL must close with a sell, i.e. is_buying_asset=False
    assert leg['is_buying_asset'] is False, 'SL leg side should be opposite of entry side (sell to close a long)'

    trigger = sl_order['trigger']['tpsl']
    assert trigger['trigger_by'] == 'MARK'
    assert trigger['trigger_price'] == '64000.0'
    assert trigger['close_position'] is False

    assert sl_order['reduce_only'] is True
    assert sl_order['metadata']['client_order_id'] == str(int(sl_order['metadata']['client_order_id']))

    print('\nSL trigger order payload (as it would be sent to GRVT):')
    import json as _json
    print(_json.dumps(sl_order, indent=2))

    print('\nOK: SL path built + signed without error, payload is well-formed.')

    await grvt.close()


asyncio.run(main())
