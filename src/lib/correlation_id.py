"""Correlation ID utilities for tracking requests across distributed services."""

import uuid
import threading
from typing import Optional
from contextvars import ContextVar

# Context variable to store current correlation ID
_correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def generate_correlation_id() -> str:
    """Generate a new unique correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id_context.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return _correlation_id_context.get()


def get_or_create_correlation_id() -> str:
    """Get the current correlation ID or create a new one if none exists."""
    correlation_id = get_correlation_id()
    if correlation_id is None:
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
    return correlation_id


class CorrelationIdManager:
    """Context manager for correlation ID lifecycle."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.previous_id = None
    
    def __enter__(self) -> str:
        """Enter the context and set the correlation ID."""
        self.previous_id = get_correlation_id()
        set_correlation_id(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore the previous correlation ID."""
        set_correlation_id(self.previous_id)


def with_correlation_id(func):
    """Decorator to ensure a function has a correlation ID."""
    def wrapper(*args, **kwargs):
        if get_correlation_id() is None:
            with CorrelationIdManager():
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper


def awith_correlation_id(func):
    """Async decorator to ensure a function has a correlation ID."""
    async def wrapper(*args, **kwargs):
        if get_correlation_id() is None:
            with CorrelationIdManager():
                return await func(*args, **kwargs)
        else:
            return await func(*args, **kwargs)
    return wrapper


def format_correlation_id(correlation_id: str) -> str:
    """Format correlation ID for logging/display."""
    return f"[{correlation_id[:8]}]"


def extract_correlation_id_from_headers(headers: dict) -> Optional[str]:
    """Extract correlation ID from HTTP headers."""
    # Common header names for correlation IDs
    header_names = [
        'x-correlation-id',
        'x-request-id', 
        'x-trace-id',
        'correlation-id',
        'request-id',
        'trace-id'
    ]
    
    for header_name in header_names:
        value = headers.get(header_name) or headers.get(header_name.upper())
        if value:
            return value
    
    return None


def add_correlation_id_to_headers(headers: dict, correlation_id: Optional[str] = None) -> dict:
    """Add correlation ID to HTTP headers."""
    if correlation_id is None:
        correlation_id = get_or_create_correlation_id()
    
    headers = headers.copy()
    headers['X-Correlation-ID'] = correlation_id
    return headers


class CorrelationIdMiddleware:
    """Middleware to handle correlation ID for web requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware to extract/inject correlation ID."""
        if scope["type"] == "http":
            # Extract correlation ID from headers
            headers = dict(scope.get("headers", []))
            header_dict = {k.decode(): v.decode() for k, v in headers.items()}
            
            correlation_id = extract_correlation_id_from_headers(header_dict)
            
            with CorrelationIdManager(correlation_id) as cid:
                # Add correlation ID to response headers
                async def send_wrapper(message):
                    if message["type"] == "http.response.start":
                        headers = list(message.get("headers", []))
                        headers.append([b"x-correlation-id", cid.encode()])
                        message["headers"] = headers
                    await send(message)
                
                await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)