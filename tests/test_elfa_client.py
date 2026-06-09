import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import json
from elfa_grvt_bot.elfa_client import ElfaClient

@pytest.fixture
def elfa_client():
    return ElfaClient(api_key="test_api_key")

@pytest.mark.asyncio
async def test_builder_chat(elfa_client):
    mock_response = {
        "sessionId": "test_session",
        "response": "Test response",
        "title": "Test title"
    }
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        
        result = await elfa_client.builder_chat("test message", "test_session")
        
        assert result == mock_response
        mock_post.assert_called_once_with(
            "https://api.elfa.ai/v2/auto/chat",
            json={"message": "Notify me when: test message", "sessionId": "test_session"}
        )

@pytest.mark.asyncio
async def test_validate_query(elfa_client):
    mock_response = {"valid": True, "errors": []}
    test_eql = {"conditions": {"AND": []}}
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        
        result = await elfa_client.validate_query(test_eql)
        
        assert result == mock_response
        mock_post.assert_called_once_with(
            "https://api.elfa.ai/v2/auto/queries/validate",
            json={"query": test_eql}
        )

@pytest.mark.asyncio
async def test_create_query(elfa_client):
    mock_response = {"id": "test_id", "status": "active"}
    test_eql = {"conditions": {"AND": []}}
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        
        result = await elfa_client.create_query("Test", "Test desc", test_eql)
        
        assert result == mock_response
        mock_post.assert_called_once_with(
            "https://api.elfa.ai/v2/auto/queries",
            json={"title": "Test", "description": "Test desc", "query": test_eql}
        )

@pytest.mark.asyncio
async def test_get_query(elfa_client):
    mock_response = {"queryId": "test_id", "status": "active"}
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        
        result = await elfa_client.get_query("test_id")
        
        assert result == mock_response
        mock_get.assert_called_once_with(
            "https://api.elfa.ai/v2/auto/queries/test_id"
        )

@pytest.mark.asyncio
async def test_cancel_query_success(elfa_client):
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        
        result = await elfa_client.cancel_query("test_id")
        
        assert result is True
        mock_post.assert_called_once_with(
            "https://api.elfa.ai/v2/auto/queries/test_id/cancel"
        )

@pytest.mark.asyncio
async def test_cancel_query_already_terminal(elfa_client):
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPStatusError(
            "409", request=MagicMock(), response=MagicMock(status_code=409)
        )
        
        result = await elfa_client.cancel_query("test_id")
        
        assert result is True

@pytest.mark.asyncio
async def test_stream_notifications(elfa_client):
    test_data = {
        "status": "triggered",
        "queryId": "test_query",
        "executionId": "test_exec",
        "triggerTime": "2026-05-20T01:59:26.965Z"
    }
    
    # Create an async generator to simulate SSE lines
    async def mock_aiter_lines():
        yield "event: notification"
        yield f"data: {json.dumps(test_data)}"
        yield ""
    
    mock_response = AsyncMock()
    mock_response.__aenter__.return_value = MagicMock()
    mock_response.__aenter__.return_value.aiter_lines = mock_aiter_lines
    
    with patch('httpx.AsyncClient.stream', return_value=mock_response):
        events = []
        async for event in elfa_client.stream_notifications("test_query"):
            events.append(event)
            
        assert len(events) == 1
        assert events[0]["event_id"] == "test_exec"
        assert events[0]["query_id"] == "test_query"
        assert events[0]["data"] == test_data
