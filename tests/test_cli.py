import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys
import json
from pathlib import Path

from elfa_grvt_bot.cli import main, handle_init, handle_strategy, handle_fire, parse_eql_input

@pytest.fixture
def mock_registry():
    return MagicMock()

@pytest.fixture
def mock_args():
    return MagicMock()

def test_parse_eql_input_json_string():
    """Test parsing EQL from JSON string."""
    eql = '{"conditions": {"AND": []}}'
    result = parse_eql_input(eql)
    assert result == {"conditions": {"AND": []}}

def test_parse_eql_input_file(tmp_path):
    """Test parsing EQL from file."""
    eql_file = tmp_path / "test_eql.json"
    eql_file.write_text('{"conditions": {"AND": []}}')
    result = parse_eql_input(str(eql_file))
    assert result == {"conditions": {"AND": []}}

def test_parse_eql_input_invalid():
    """Test parsing invalid EQL input."""
    with pytest.raises(ValueError):
        parse_eql_input("not valid json")

def test_handle_init(tmp_path):
    """Test init command."""
    args = MagicMock()
    args.target_dir = str(tmp_path)
    
    result = handle_init(args)
    
    assert result == 0
    assert (tmp_path / ".env").exists()

def test_handle_init_existing_dir(tmp_path):
    """Test init command with existing directory."""
    (tmp_path / ".env").touch()
    
    args = MagicMock()
    args.target_dir = str(tmp_path)
    
    result = handle_init(args)
    
    assert result == 0

@patch("elfa_grvt_bot.cli.Registry")
def test_handle_strategy_list(mock_registry_class):
    """Test strategy list command."""
    mock_registry = MagicMock()
    mock_registry.list_strategies.return_value = [{"query_id": "test1"}]
    mock_registry_class.return_value = mock_registry
    
    args = MagicMock()
    args.strategy_command = "list"
    args.status = "active"
    
    result = handle_strategy(args)
    
    assert result == 0
    mock_registry.list_strategies.assert_called_once_with(status="active")

@patch("elfa_grvt_bot.cli.Registry")
def test_handle_strategy_create(mock_registry_class):
    """Test strategy create command."""
    mock_registry = MagicMock()
    mock_registry.create_strategy.return_value = "test123"
    mock_registry_class.return_value = mock_registry
    
    args = MagicMock()
    args.strategy_command = "create"
    args.title = "Test"
    args.description = "Test desc"
    args.eql = '{"conditions": {"AND": []}}'
    args.side = "buy"
    args.symbol = "BTC_USDT_Perp"
    args.amount = 0.1
    args.order_type = "market"
    args.price = None
    args.tp_pct = None
    args.sl_pct = None
    args.leverage = None
    args.max_notional = 1000.0
    
    result = handle_strategy(args)
    
    assert result == 0
    mock_registry.create_strategy.assert_called_once()

@patch("elfa_grvt_bot.cli.Registry")
def test_handle_fire_list(mock_registry_class):
    """Test fire list command."""
    mock_registry = MagicMock()
    mock_registry.list_fires.return_value = [{"event_id": "test1"}]
    mock_registry_class.return_value = mock_registry
    
    args = MagicMock()
    args.fire_command = "list"
    args.query_id = "test123"
    args.outcome = "placed"
    
    result = handle_fire(args)
    
    assert result == 0
    mock_registry.list_fires.assert_called_once_with(query_id="test123", outcome="placed")

def test_main_help(capsys):
    """Test main help output."""
    with patch("sys.argv", ["elfa-grvt-bot", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
    
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
