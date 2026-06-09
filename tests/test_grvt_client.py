import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime
from elfa_grvt_bot.grvt_client import GrvtClient

@pytest.fixture
def grvt_client():
    return GrvtClient(api_key="test_api_key", private_key="test_private_key")

@pytest.mark.asyncio
async def test_login_success(grvt_client):
    mock_response = MagicMock()
    mock_response.headers = {"set-cookie": "gravity=test_cookie"}
    mock_response.json.return_value = {"sub_account_id": "test_account_id"}
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await grvt_client.login()
        
        assert result is True
        assert grvt_client.account_id == "test_account_id"
        assert grvt_client.cookie == "test_cookie"
        mock_post.assert_called_once_with(
            "https://edge.grvt.io/auth/api_key/login",
            json={"api_key": "test_api_key"}
        )

@pytest.mark.asyncio
async def test_login_failure(grvt_client):
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_response.json.return_value = {"error": "Invalid API key"}
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        with pytest.raises(ValueError) as excinfo:
            await grvt_client.login()
        
        assert "GRVT login failed" in str(excinfo.value)

@pytest.mark.asyncio
async def test_fetch_mid_price_mark(grvt_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"mark_price": "50000.0"}
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await grvt_client.fetch_mid_price("BTC_USDT_Perp")
        
        assert result == Decimal("50000.0")
        mock_get.assert_called_once_with(
            "https://market-data.grvt.io/market-data/v1/instruments/BTC_USDT_Perp/ticker"
        )

@pytest.mark.asyncio
async def test_fetch_mid_price_bid_ask(grvt_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"best_bid": "49900.0", "best_ask": "50100.0"}
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await grvt_client.fetch_mid_price("BTC_USDT_Perp")
        
        assert result == Decimal("50000.0")

@pytest.mark.asyncio
async def test_place_entry_with_tpsl(grvt_client):
    # Setup authenticated client
    grvt_client.account_id = "test_account_id"
    grvt_client.cookie = "test_cookie"
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [
        {"order_id": "parent_123"},
        {"order_id": "tp_456"},
        {"order_id": "sl_789"}
    ]}
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await grvt_client.place_entry_with_tpsl(
            symbol="BTC_USDT_Perp",
            entry_side="buy",
            amount=Decimal("0.1"),
            order_type="market",
            tp_price=Decimal("51000.0"),
            sl_price=Decimal("49000.0")
        )
        
        assert result["parent_order_id"] == "parent_123"
        assert result["tp_order_id"] == "tp_456"
        assert result["sl_order_id"] == "sl_789"
        
        # Verify headers and body structure
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://trades.grvt.io/full/v2/bulk_orders"
        assert kwargs["headers"]["Cookie"] == "gravity=test_cookie"
        assert kwargs["headers"]["X-Grvt-Account-Id"] == "test_account_id"
        
        body = kwargs["json"]
        assert body["sub_account_id"] == "test_account_id"
        assert len(body["orders"]) == 3  # parent + tp + sl

@pytest.mark.asyncio
async def test_place_entry_without_tpsl(grvt_client):
    # Setup authenticated client
    grvt_client.account_id = "test_account_id"
    grvt_client.cookie = "test_cookie"
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [
        {"order_id": "parent_123"}
    ]}
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await grvt_client.place_entry_with_tpsl(
            symbol="BTC_USDT_Perp",
            entry_side="buy",
            amount=Decimal("0.1"),
            order_type="market"
        )
        
        assert result["parent_order_id"] == "parent_123"
        assert result["tp_order_id"] is None
        assert result["sl_order_id"] is None
        
        # Should only have parent order
        body = mock_post.call_args[1]["json"]
        assert len(body["orders"]) == 1