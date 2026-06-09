import httpx
import json
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime

class ElfaClient:
    """
    Client for interacting with the Elfa Auto API.
    Implements all endpoints specified in references/02-protocols.md
    """
    
    def __init__(self, api_key: str):
        self.base_url = "https://api.elfa.ai"
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"x-elfa-api-key": self.api_key},
            timeout=30.0
        )
    
    async def builder_chat(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        POST /v2/auto/chat - Builder Chat endpoint
        Always prepends "Notify me when: " to the message
        """
        prefixed_msg = f"Notify me when: {message}"
        response = await self.client.post(
            f"{self.base_url}/v2/auto/chat",
            json={"message": prefixed_msg, "sessionId": session_id}
        )
        response.raise_for_status()
        return response.json()
    
    async def validate_query(self, eql: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /v2/auto/queries/validate - Validate EQL
        Wraps the inner EQL in {'query': ...} as required by the API
        """
        response = await self.client.post(
            f"{self.base_url}/v2/auto/queries/validate",
            json={"query": eql}
        )
        response.raise_for_status()
        return response.json()
    
    async def create_query(self, title: str, description: str, eql: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /v2/auto/queries - Create a new query
        """
        response = await self.client.post(
            f"{self.base_url}/v2/auto/queries",
            json={
                "title": title,
                "description": description,
                "query": eql
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_query(self, query_id: str) -> Dict[str, Any]:
        """
        GET /v2/auto/queries/{id} - Poll query status
        """
        response = await self.client.get(
            f"{self.base_url}/v2/auto/queries/{query_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def cancel_query(self, query_id: str) -> bool:
        """
        POST /v2/auto/queries/{id}/cancel - Cancel a query
        Returns True if successful or already terminal (409)
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/v2/auto/queries/{query_id}/cancel"
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:  # Already terminal
                return True
            raise
    
    async def stream_notifications(self, query_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        GET /v2/auto/queries/{id}/stream - SSE stream
        Parses frames according to production schema in references/02-protocols.md
        """
        async with httpx.AsyncClient(
            headers={
                "x-elfa-api-key": self.api_key,
                "Accept": "text/event-stream"
            },
            timeout=None
        ) as sse_client:
            
            async with sse_client.stream(
                "GET",
                f"{self.base_url}/v2/auto/queries/{query_id}/stream"
            ) as response:
                response.raise_for_status()
                
                current_event = None
                current_id = None
                data_lines = []
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    
                    # Skip comments/keep-alives
                    if line.startswith(':'):
                        continue
                    
                    # End of frame - process if we have a complete event
                    if line == '':
                        if current_event == 'notification' and data_lines:
                            try:
                                payload = json.loads(''.join(data_lines))
                                if payload.get('status') == 'triggered':
                                    yield {
                                        'event_id': payload['executionId'],
                                        'query_id': payload['queryId'],
                                        'data': payload
                                    }
                            except json.JSONDecodeError:
                                pass
                        
                        current_event = None
                        current_id = None
                        data_lines = []
                        continue
                    
                    # Parse SSE fields
                    if ':' not in line:
                        continue
                    
                    field, _, value = line.partition(':')
                    value = value[1:] if value.startswith(' ') else value
                    
                    if field == 'event':
                        current_event = value.strip()
                    elif field == 'id':
                        current_id = value.strip()
                    elif field == 'data':
                        data_lines.append(value)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()