import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import os

from elfa_grvt_bot.preflight import Preflight, PreflightError

@pytest.fixture
def preflight():
    return Preflight()

@pytest.mark.asyncio
async def test_check_env_vars_success(preflight):
    """Test env var check with all vars present."""
    with patch.dict(
        "os.environ", 
        {
            "ELFA_API_KEY": "test_elfa",
            "GRVT_TRADING_API_KEY": "test_grvt_key",
            "GRVT_TRADING_PRIVATE_KEY": "test_grvt_priv"
        },
        clear=True
    ):
        result = await preflight.check_env_vars()
        assert result is True

@pytest.mark.asyncio
async def test_check_env_vars_failure(preflight):
    """Test env var check with missing vars."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(PreflightError):
            await preflight.check_env_vars()

@pytest.mark.asyncio
@patch("elfa_grvt_bot.preflight.ElfaClient")
async def test_check_elfa_connection_success(mock_client_class, preflight):
    """Test successful Elfa connection."""
    mock_client = AsyncMock()
    mock_client.validate_query.return_value = {"valid": True}
    mock_client_class.return_value = mock_client
    
    with patch.dict("os.environ", {"ELFA_API_KEY": "test"}, clear=True):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(json=lambda: {"valid": True})
            result = await preflight.check_elfa_connection()
        assert result is True

@pytest.mark.asyncio
@patch("elfa_grvt_bot.preflight.ElfaClient")
async def test_check_elfa_connection_failure(mock_client_class, preflight):
    """Test failed Elfa connection."""
    mock_client = AsyncMock()
    mock_client.validate_query.side_effect = Exception("Connection failed")
    mock_client_class.return_value = mock_client
    
    with patch.dict("os.environ", {"ELFA_API_KEY": "test"}, clear=True):
        with pytest.raises(PreflightError):
            await preflight.check_elfa_connection()

@pytest.mark.asyncio
@patch("elfa_grvt_bot.preflight.GrvtClient")
async def test_check_grvt_connection_success(mock_client_class, preflight):
    """Test successful GRVT connection."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.headers.get.return_value = "gravity=test_cookie"
    mock_response.json.return_value = {"sub_account_id": "test"}
    mock_client.login.return_value = True
    mock_client_class.return_value = mock_client
    
    with patch.dict("os.environ", {
        "GRVT_TRADING_API_KEY": "test_key",
        "GRVT_TRADING_PRIVATE_KEY": "test_priv"
    }, clear=True):
        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await preflight.check_grvt_connection()
        assert result is True

@pytest.mark.asyncio
@patch("elfa_grvt_bot.preflight.GrvtClient")
async def test_check_grvt_connection_failure(mock_client_class, preflight):
    """Test failed GRVT connection."""
    mock_client = AsyncMock()
    mock_client.login.side_effect = Exception("Login failed")
    mock_client_class.return_value = mock_client
    
    with patch.dict("os.environ", {
        "GRVT_TRADING_API_KEY": "test_key",
        "GRVT_TRADING_PRIVATE_KEY": "test_priv"
    }, clear=True):
        with pytest.raises(PreflightError):
            await preflight.check_grvt_connection()

@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_check_telegram_config_success(mock_client_class, preflight):
    """Test successful Telegram config check."""
    mock_client = AsyncMock()
    mock_client.get.return_value = MagicMock(json=lambda: {"ok": True})
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "test_chat"
    }, clear=True):
        result = await preflight.check_telegram_config()
        assert result is True

@pytest.mark.asyncio
async def test_check_telegram_config_disabled(preflight):
    """Test disabled Telegram config."""
    with patch.dict("os.environ", {}, clear=True):
        result = await preflight.check_telegram_config()
        assert result is True

@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_check_telegram_config_failure(mock_client_class, preflight):
    """Test failed Telegram config."""
    mock_client = AsyncMock()
    mock_client.get.return_value = MagicMock(json=lambda: {"ok": False})
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "test_chat"
    }, clear=True):
        with pytest.raises(PreflightError):
            await preflight.check_telegram_config()

@pytest.mark.asyncio
@patch("elfa_grvt_bot.preflight.Preflight.check_env_vars")
@patch("elfa_grvt_bot.preflight.Preflight.check_elfa_connection")
@patch("elfa_grvt_bot.preflight.Preflight.check_grvt_connection")
@patch("elfa_grvt_bot.preflight.Preflight.check_telegram_config")
async def test_run_checks_all_pass(
    mock_telegram, mock_grvt, mock_elfa, mock_env, preflight
):
    """Test run_checks with all checks passing."""
    mock_env.return_value = True
    mock_elfa.return_value = True
    mock_grvt.return_value = True
    mock_telegram.return_value = True
    
    result = await preflight.run_checks()
    assert result is True

@pytest.mark.asyncio
@patch("elfa_grvt_bot.preflight.Preflight.check_env_vars")
@patch("elfa_grvt_bot.preflight.Preflight.check_elfa_connection")
@patch("elfa_grvt_bot.preflight.Preflight.check_grvt_connection")
@patch("elfa_grvt_bot.preflight.Preflight.check_telegram_config")
async def test_run_checks_one_fails(
    mock_telegram, mock_grvt, mock_elfa, mock_env, preflight
):
    """Test run_checks with one check failing."""
    mock_env.return_value = True
    mock_elfa.return_value = True
    mock_grvt.side_effect = PreflightError("GRVT failed")
    mock_telegram.return_value = True
    
    result = await preflight.run_checks()
    assert result is False