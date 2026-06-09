import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from elfa_grvt_bot.core import Core, Reject, Allow

@pytest.fixture
def core():
    registry = AsyncMock()
    elfa = AsyncMock()
    grvt = AsyncMock()
    alerts = AsyncMock()
    return Core(registry, elfa, grvt, alerts)

@pytest.mark.asyncio
async def test_check_guardrails_pass(core):
    strategy = {
        'amount': '0.1',
        'max_notional_usd': '10000.0',
        'env': 'prod'
    }
    assert isinstance(core.check_guardrails(strategy, Decimal('50000.0')), Allow)

@pytest.mark.asyncio
async def test_check_guardrails_fail_notional(core):
    strategy = {
        'amount': '0.1',
        'max_notional_usd': '1000.0',
        'env': 'prod'
    }
    result = core.check_guardrails(strategy, Decimal('20000.0'))
    assert isinstance(result, Reject)
    assert "exceeds max" in result.reason

@pytest.mark.asyncio
async def test_check_guardrails_fail_env(core):
    strategy = {
        'amount': '0.1',
        'max_notional_usd': '10000.0',
        'env': 'test'
    }
    result = core.check_guardrails(strategy, Decimal('50000.0'))
    assert isinstance(result, Reject)
    assert "expected prod" in result.reason

@pytest.mark.asyncio
async def test_check_guardrails_fail_amount(core):
    strategy = {
        'amount': '-0.1',
        'max_notional_usd': '1000.0',
        'env': 'prod'
    }
    result = core.check_guardrails(strategy, Decimal('50000.0'))
    assert isinstance(result, Reject)
    assert "must be positive" in result.reason

@pytest.mark.asyncio
async def test_compute_target_price_long_tp(core):
    price = core.compute_target_price(50000.0, 1.0, 'buy', 'tp')
    assert pytest.approx(price) == 50500.0

@pytest.mark.asyncio
async def test_compute_target_price_long_sl(core):
    price = core.compute_target_price(50000.0, 1.0, 'buy', 'sl')
    assert pytest.approx(price) == 49500.0

@pytest.mark.asyncio
async def test_compute_target_price_short_tp(core):
    price = core.compute_target_price(50000.0, 1.0, 'sell', 'tp')
    assert pytest.approx(price) == 49500.0

@pytest.mark.asyncio
async def test_compute_target_price_short_sl(core):
    price = core.compute_target_price(50000.0, 1.0, 'sell', 'sl')
    assert pytest.approx(price) == 50500.0

@pytest.mark.asyncio
async def test_align_tick_down(core):
    aligned = core.align_tick(50001.23, 0.1, 'down')
    assert aligned == 50001.2

@pytest.mark.asyncio
async def test_align_tick_up(core):
    aligned = core.align_tick(50001.23, 0.1, 'up')
    assert aligned == 50001.3

@pytest.mark.asyncio
async def test_align_tick_nearest(core):
    aligned = core.align_tick(50001.25, 0.1, 'nearest')
    assert aligned == 50001.2

@pytest.mark.asyncio
async def test_process_fire_success(core):
    # Setup mocks
    test_strategy = {
        'query_id': 'test_query',
        'title': 'Test Strategy',
        'side': 'buy',
        'amount': '0.1',
        'symbol': 'BTC_USDT_Perp',
        'order_type': 'market',
        'max_notional_usd': '10000.0',
        'env': 'prod'
    }
    
    core.registry.get_strategy.return_value = test_strategy
    core.grvt.fetch_mid_price.return_value = Decimal('50000.0')
    core.grvt.tick_size.return_value = Decimal('0.1')
    core.grvt.place_entry_with_tpsl.return_value = {
        'parent_order_id': 'order_123'
    }
    
    # Run test
    await core.process_fire('test_event', 'test_query', {'status': 'triggered'})
    
    # Verify calls
    core.registry.add_fire.assert_called_once()
    core.grvt.fetch_mid_price.assert_called_once_with('BTC_USDT_Perp')
    core.grvt.place_entry_with_tpsl.assert_called_once()
    core.registry.update_fire_outcome.assert_called_once()
    core.alerts.emit.assert_any_call('info', 'trigger_received', 
                                   'Elfa trigger fired: Test Strategy. Placing BUY 0.1 BTC_USDT_Perp (market) on GRVT',
                                   query_id='test_query', fire_event_id='test_event')

@pytest.mark.asyncio
async def test_process_fire_guardrail_reject(core):
    # Setup mocks
    test_strategy = {
        'query_id': 'test_query',
        'title': 'Test Strategy',
        'side': 'buy',
        'amount': '0.1',
        'symbol': 'BTC_USDT_Perp',
        'order_type': 'market',
        'max_notional_usd': '1000.0',
        'env': 'prod'
    }
    
    core.registry.get_strategy.return_value = test_strategy
    core.grvt.fetch_mid_price.return_value = Decimal('20000.0')  # Will trigger notional guardrail
    
    # Run test
    await core.process_fire('test_event', 'test_query', {'status': 'triggered'})
    
    # Verify rejection
    core.registry.update_fire_outcome.assert_called_once_with(
        'test_event', 'rejected_guardrail', 'notional $2000.00 exceeds max $1000.00')
    core.registry.update_strategy_status.assert_called_once_with('test_query', 'fired')
    core.alerts.emit.assert_any_call('warning', 'guardrail_rejected', 'fire rejected: notional $2000.00 exceeds max $1000.00',
                                   query_id='test_query', fire_event_id='test_event')
