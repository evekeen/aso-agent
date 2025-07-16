"""Unit tests for correlation ID utilities."""

import pytest
from unittest.mock import patch
import uuid

from lib.correlation_id import (
    generate_correlation_id,
    set_correlation_id, 
    get_correlation_id,
    get_or_create_correlation_id,
    CorrelationIdManager,
    with_correlation_id,
    awith_correlation_id,
    format_correlation_id,
    extract_correlation_id_from_headers,
    add_correlation_id_to_headers
)


def test_generate_correlation_id():
    """Test correlation ID generation."""
    cid1 = generate_correlation_id()
    cid2 = generate_correlation_id()
    
    # Should be valid UUIDs
    assert uuid.UUID(cid1)
    assert uuid.UUID(cid2)
    
    # Should be unique
    assert cid1 != cid2


def test_set_get_correlation_id():
    """Test setting and getting correlation ID."""
    test_id = "test-123"
    
    # Initially should be None
    assert get_correlation_id() is None
    
    # Set and get
    set_correlation_id(test_id)
    assert get_correlation_id() == test_id
    
    # Clear
    set_correlation_id(None)
    assert get_correlation_id() is None


def test_get_or_create_correlation_id():
    """Test getting or creating correlation ID."""
    # Clear any existing ID
    set_correlation_id(None)
    
    # Should create a new one
    cid1 = get_or_create_correlation_id()
    assert cid1 is not None
    assert get_correlation_id() == cid1
    
    # Should return the same one
    cid2 = get_or_create_correlation_id()
    assert cid2 == cid1


def test_correlation_id_manager():
    """Test correlation ID context manager."""
    # Clear any existing ID
    set_correlation_id(None)
    
    test_id = "test-manager-123"
    
    # Use context manager
    with CorrelationIdManager(test_id) as cid:
        assert cid == test_id
        assert get_correlation_id() == test_id
    
    # Should be cleared after context
    assert get_correlation_id() is None


def test_correlation_id_manager_nested():
    """Test nested correlation ID context managers."""
    set_correlation_id(None)
    
    outer_id = "outer-123"
    inner_id = "inner-456"
    
    with CorrelationIdManager(outer_id):
        assert get_correlation_id() == outer_id
        
        with CorrelationIdManager(inner_id):
            assert get_correlation_id() == inner_id
        
        # Should restore outer ID
        assert get_correlation_id() == outer_id
    
    # Should be cleared after all contexts
    assert get_correlation_id() is None


def test_correlation_id_manager_auto_generate():
    """Test auto-generation in context manager."""
    set_correlation_id(None)
    
    with CorrelationIdManager() as cid:
        assert cid is not None
        assert get_correlation_id() == cid
        # Should be a valid UUID
        assert uuid.UUID(cid)


def test_with_correlation_id_decorator():
    """Test correlation ID decorator."""
    set_correlation_id(None)
    
    @with_correlation_id
    def test_func():
        return get_correlation_id()
    
    # Should create a correlation ID
    result = test_func()
    assert result is not None
    assert uuid.UUID(result)
    
    # Should be cleared after function
    assert get_correlation_id() is None


def test_with_correlation_id_decorator_existing():
    """Test decorator with existing correlation ID."""
    existing_id = "existing-123"
    set_correlation_id(existing_id)
    
    @with_correlation_id
    def test_func():
        return get_correlation_id()
    
    # Should use existing ID
    result = test_func()
    assert result == existing_id
    assert get_correlation_id() == existing_id


@pytest.mark.anyio
async def test_awith_correlation_id_decorator():
    """Test async correlation ID decorator."""
    set_correlation_id(None)
    
    @awith_correlation_id
    async def test_func():
        return get_correlation_id()
    
    # Should create a correlation ID
    result = await test_func()
    assert result is not None
    assert uuid.UUID(result)
    
    # Should be cleared after function
    assert get_correlation_id() is None


def test_format_correlation_id():
    """Test correlation ID formatting."""
    test_id = "12345678-1234-5678-9012-123456789012"
    formatted = format_correlation_id(test_id)
    assert formatted == "[12345678]"


def test_extract_correlation_id_from_headers():
    """Test extracting correlation ID from headers."""
    # Test various header names
    headers = {"x-correlation-id": "test-123"}
    assert extract_correlation_id_from_headers(headers) == "test-123"
    
    headers = {"X-CORRELATION-ID": "test-456"}
    assert extract_correlation_id_from_headers(headers) == "test-456"
    
    headers = {"x-request-id": "test-789"}
    assert extract_correlation_id_from_headers(headers) == "test-789"
    
    headers = {"correlation-id": "test-abc"}
    assert extract_correlation_id_from_headers(headers) == "test-abc"
    
    # Test no header
    headers = {"other-header": "value"}
    assert extract_correlation_id_from_headers(headers) is None
    
    # Test empty headers
    assert extract_correlation_id_from_headers({}) is None


def test_add_correlation_id_to_headers():
    """Test adding correlation ID to headers."""
    set_correlation_id(None)
    
    headers = {"content-type": "application/json"}
    
    # Should add correlation ID
    result = add_correlation_id_to_headers(headers)
    assert "X-Correlation-ID" in result
    assert result["content-type"] == "application/json"
    
    # Original headers should be unchanged
    assert "X-Correlation-ID" not in headers


def test_add_correlation_id_to_headers_specific():
    """Test adding specific correlation ID to headers."""
    test_id = "specific-123"
    headers = {"content-type": "application/json"}
    
    result = add_correlation_id_to_headers(headers, test_id)
    assert result["X-Correlation-ID"] == test_id
    assert result["content-type"] == "application/json"


def test_add_correlation_id_to_headers_existing_context():
    """Test adding correlation ID from context to headers."""
    test_id = "context-123"
    set_correlation_id(test_id)
    
    headers = {"content-type": "application/json"}
    
    result = add_correlation_id_to_headers(headers)
    assert result["X-Correlation-ID"] == test_id
    
    # Clean up
    set_correlation_id(None)