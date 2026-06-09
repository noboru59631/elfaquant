import pytest
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from elfa_grvt_bot.registry import Registry

@pytest.fixture
def registry(tmp_path):
    db_path = tmp_path / "test_registry.db"
    return Registry(str(db_path))

def test_ensure_db(registry):
    """Test that the database and tables are created correctly."""
    with sqlite3.connect(registry.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "strategies" in tables
        assert "fires" in tables
        assert "alerts" in tables

def test_add_strategy(registry):
    """Test adding a strategy to the registry."""
    eql_json = '{"conditions": {"AND": [{"source": "ta", "method": "rsi", "args": {"symbol": "BTC", "timeframe": "1h", "period": 14}, "operator": "crosses_below", "value": 30}]}, "actions": [{"type": "notify"}]}'
    assert registry.add_strategy(
        query_id="test_query_id",
        title="BTC RSI oversold on 1h",
        description="Buy signal when 1h RSI dips below 30",
        eql_json=eql_json,
        symbol="BTC_USDT_Perp",
        side="buy",
        amount=0.1,
        order_type="market",
        price=None,
        leverage=5,
        max_notional_usd=1000.0,
        tp_pct=1.5,
        sl_pct=1.0
    )

    strategy = registry.get_strategy("test_query_id")
    assert strategy is not None
    assert strategy["title"] == "BTC RSI oversold on 1h"
    assert strategy["status"] == "active"

def test_update_strategy_status(registry):
    """Test updating the status of a strategy."""
    eql_json = '{"conditions": {"AND": [{"source": "ta", "method": "rsi", "args": {"symbol": "BTC", "timeframe": "1h", "period": 14}, "operator": "crosses_below", "value": 30}]}, "actions": [{"type": "notify"}]}'
    registry.add_strategy(
        query_id="test_query_id",
        title="BTC RSI oversold on 1h",
        description="Buy signal when 1h RSI dips below 30",
        eql_json=eql_json,
        symbol="BTC_USDT_Perp",
        side="buy",
        amount=0.1,
        order_type="market",
        price=None,
        leverage=5,
        max_notional_usd=1000.0,
        tp_pct=1.5,
        sl_pct=1.0
    )

    assert registry.update_strategy_status("test_query_id", "fired")
    strategy = registry.get_strategy("test_query_id")
    assert strategy["status"] == "fired"

def test_add_fire(registry):
    """Test adding a fire record to the registry."""
    eql_json = '{"conditions": {"AND": [{"source": "ta", "method": "rsi", "args": {"symbol": "BTC", "timeframe": "1h", "period": 14}, "operator": "crosses_below", "value": 30}]}, "actions": [{"type": "notify"}]}'
    registry.add_strategy(
        query_id="test_query_id",
        title="BTC RSI oversold on 1h",
        description="Buy signal when 1h RSI dips below 30",
        eql_json=eql_json,
        symbol="BTC_USDT_Perp",
        side="buy",
        amount=0.1,
        order_type="market",
        price=None,
        leverage=5,
        max_notional_usd=1000.0,
        tp_pct=1.5,
        sl_pct=1.0
    )

    raw_payload = '{"status": "triggered", "queryId": "test_query_id", "executionId": "test_event_id", "triggerTime": "2026-05-20T01:50:10.965Z"}'
    assert registry.add_fire(
        event_id="test_event_id",
        query_id="test_query_id",
        raw_payload=raw_payload,
        outcome="placed",
        parent_order_id="order_123",
        tp_order_id="order_124",
        sl_order_id="order_125",
        reference_price=50000.0,
        tp_price=50750.0,
        sl_price=49500.0
    )

def test_add_alert(registry):
    """Test adding an alert to the registry."""
    alert_id = registry.add_alert(
        severity="info",
        category="trigger_received",
        message="SSE delivered a fire; order placement about to start",
        query_id="test_query_id",
        fire_event_id="test_event_id"
    )
    assert alert_id is not None

def test_get_unacked_alerts(registry):
    """Test retrieving unacknowledged alerts."""
    registry.add_alert(
        severity="info",
        category="trigger_received",
        message="SSE delivered a fire; order placement about to start",
        query_id="test_query_id",
        fire_event_id="test_event_id"
    )

    alerts = registry.get_unacked_alerts()
    assert len(alerts) == 1
    assert alerts[0]["category"] == "trigger_received"

def test_ack_alert(registry):
    """Test acknowledging an alert."""
    alert_id = registry.add_alert(
        severity="info",
        category="trigger_received",
        message="SSE delivered a fire; order placement about to start",
        query_id="test_query_id",
        fire_event_id="test_event_id"
    )

    assert registry.ack_alert(alert_id)
    alerts = registry.get_unacked_alerts()
    assert len(alerts) == 0