"""HTTP client for ASO Agent Service."""

import httpx
import json
import os
from typing import AsyncGenerator, Dict, Any, Optional

from src.schema.schema import UserInput, StreamInput, ChatMessage, ServiceMetadata, ChatHistory


class AgentClientError(Exception):
    """Exception raised by the agent client."""
    pass


class AgentClient:
    """Client for interacting with the ASO agent service."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        agent: str = "aso-agent",
        timeout: float = 300.0,  # 5 minutes for long ASO analyses
        get_info: bool = True,
    ):
        self.base_url = base_url.rstrip('/')
        self.agent = agent
        self.timeout = timeout
        self.auth_secret = os.getenv("AUTH_SECRET")
        self.info: Optional[ServiceMetadata] = None
        
        if get_info:
            self.retrieve_info()
    
    @property
    def _headers(self) -> Dict[str, str]:
        """Get headers for requests."""
        headers = {"Content-Type": "application/json"}
        if self.auth_secret:
            headers["Authorization"] = f"Bearer {self.auth_secret}"
        return headers
    
    def retrieve_info(self) -> None:
        """Retrieve service metadata."""
        try:
            response = httpx.get(
                f"{self.base_url}/info",
                headers=self._headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.info = ServiceMetadata.model_validate(response.json())
        except httpx.HTTPError as e:
            raise AgentClientError(f"Error getting service info: {e}")
    
    def update_agent(self, agent: str) -> None:
        """Update the agent to use."""
        if self.info and agent not in [a.key for a in self.info.agents]:
            raise AgentClientError(f"Agent '{agent}' not available")
        self.agent = agent
    
    async def ainvoke(
        self,
        message: str,
        model: str = "gpt-4o-mini",
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Invoke the ASO agent with a single request."""
        
        user_input = UserInput(
            message=message,
            model=model,
            thread_id=thread_id,
            user_id=user_id,
            agent_config=agent_config or {}
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/{self.agent}/invoke",
                    json=user_input.model_dump(),
                    headers=self._headers,
                )
                response.raise_for_status()
                return ChatMessage.model_validate(response.json())
            except httpx.HTTPError as e:
                raise AgentClientError(f"Error invoking agent: {e}")
    
    async def astream(
        self,
        message: str,
        model: str = "gpt-4o-mini",
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        stream_tokens: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses from the ASO agent."""
        
        stream_input = StreamInput(
            message=message,
            model=model,
            thread_id=thread_id,
            user_id=user_id,
            agent_config=agent_config or {},
            stream_tokens=stream_tokens
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/{self.agent}/stream",
                    json=stream_input.model_dump(),
                    headers=self._headers,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        parsed = self._parse_stream_line(line)
                        if parsed is not None:
                            yield parsed
                            
            except httpx.HTTPError as e:
                raise AgentClientError(f"Error streaming from agent: {e}")
    
    def _parse_stream_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single line from the SSE stream."""
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                return None
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                raise AgentClientError(f"Error parsing stream data: {e}")
        return None
    
    def invoke(
        self,
        message: str,
        model: str = "gpt-4o-mini",
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Synchronous version of invoke."""
        import asyncio
        return asyncio.run(self.ainvoke(
            message, model, thread_id, user_id, agent_config
        ))
    
    async def get_history(self, thread_id: str) -> ChatHistory:
        """Get conversation history for a thread."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/history/{thread_id}",
                    headers=self._headers,
                )
                response.raise_for_status()
                return ChatHistory.model_validate(response.json())
            except httpx.HTTPError as e:
                raise AgentClientError(f"Error getting history: {e}")
    
    async def record_feedback(
        self,
        run_id: str,
        rating: int,
        comment: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record feedback for a response."""
        from src.schema.schema import Feedback
        
        feedback = Feedback(
            run_id=run_id,
            rating=rating,
            comment=comment,
            user_id=user_id
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/feedback",
                    json=feedback.model_dump(),
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise AgentClientError(f"Error recording feedback: {e}")