"""Unit tests for progress reporter functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from aso_playwright_service.progress_reporter import (
    ProgressReporter,
    with_progress_tracking,
    get_progress_reporter
)


@pytest.fixture
def mock_session():
    """Mock aiohttp session."""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    session.post.return_value.__aenter__.return_value = response
    return session


@pytest.mark.anyio
async def test_progress_reporter_init():
    """Test ProgressReporter initialization."""
    reporter = ProgressReporter("test-correlation-id")
    assert reporter.correlation_id == "test-correlation-id"
    assert reporter.main_service_url == "http://localhost:8000"
    assert reporter.session is None


@pytest.mark.anyio
async def test_progress_reporter_context_manager():
    """Test ProgressReporter as context manager."""
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        
        reporter = ProgressReporter("test-correlation-id")
        
        async with reporter:
            assert reporter.session == mock_session
        
        mock_session.close.assert_called_once()


@pytest.mark.anyio
async def test_report_step(mock_session):
    """Test reporting a step."""
    reporter = ProgressReporter("test-correlation-id")
    reporter.session = mock_session
    
    await reporter.report_step("test_step", "Test step description", 50.0)
    
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    
    assert call_args[1]["json"]["correlation_id"] == "test-correlation-id"
    assert call_args[1]["json"]["event_type"] == "step_progress"
    assert call_args[1]["json"]["step_name"] == "test_step"
    assert call_args[1]["json"]["description"] == "Test step description"
    assert call_args[1]["json"]["progress_percentage"] == 50.0


@pytest.mark.anyio
async def test_report_error(mock_session):
    """Test reporting an error."""
    reporter = ProgressReporter("test-correlation-id")
    reporter.session = mock_session
    
    await reporter.report_error(
        "Test error message",
        "ValueError",
        "test_step",
        retry_attempt=2
    )
    
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    
    assert call_args[1]["json"]["correlation_id"] == "test-correlation-id"
    assert call_args[1]["json"]["event_type"] == "error"
    assert call_args[1]["json"]["error_message"] == "Test error message"
    assert call_args[1]["json"]["error_type"] == "ValueError"
    assert call_args[1]["json"]["step_name"] == "test_step"
    assert call_args[1]["json"]["retry_attempt"] == 2


@pytest.mark.anyio
async def test_report_keywords_processed(mock_session):
    """Test reporting keyword processing results."""
    reporter = ProgressReporter("test-correlation-id")
    reporter.session = mock_session
    
    keywords = {"keyword1": {"difficulty": 50.0, "traffic": 75.0}}
    await reporter.report_keywords_processed(keywords, 2)
    
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    
    assert call_args[1]["json"]["correlation_id"] == "test-correlation-id"
    assert call_args[1]["json"]["event_type"] == "keywords_processed"
    assert call_args[1]["json"]["keywords_processed"] == 1
    assert call_args[1]["json"]["total_keywords"] == 2
    assert call_args[1]["json"]["progress_percentage"] == 50.0


@pytest.mark.anyio
async def test_with_progress_tracking_decorator():
    """Test the progress tracking decorator."""
    
    class MockTask:
        def __init__(self):
            self.progress_reporter = AsyncMock()
    
    task = MockTask()
    
    @with_progress_tracking("test_step", "Test step description")
    async def test_method(self):
        return "success"
    
    # Bind the method to the task instance
    result = await test_method(task)
    
    assert result == "success"
    assert task.progress_reporter.report_step.call_count == 2
    
    # Check first call (start)
    first_call = task.progress_reporter.report_step.call_args_list[0]
    assert first_call[0] == ("test_step", "Test step description")
    
    # Check second call (completion)
    second_call = task.progress_reporter.report_step.call_args_list[1]
    assert second_call[0] == ("test_step", "Completed Test step description", 100.0)


@pytest.mark.anyio
async def test_with_progress_tracking_decorator_error():
    """Test the progress tracking decorator with error handling."""
    
    class MockTask:
        def __init__(self):
            self.progress_reporter = AsyncMock()
    
    task = MockTask()
    
    @with_progress_tracking("test_step", "Test step description")
    async def test_method(self):
        raise ValueError("Test error")
    
    # Bind the method to the task instance
    with pytest.raises(ValueError, match="Test error"):
        await test_method(task)
    
    # Should report start and error, but not completion
    assert task.progress_reporter.report_step.call_count == 1
    assert task.progress_reporter.report_error.call_count == 1
    
    # Check error call
    error_call = task.progress_reporter.report_error.call_args
    assert error_call[1]["error_message"] == "Test error"
    assert error_call[1]["error_type"] == "ValueError"
    assert error_call[1]["step_name"] == "test_step"


@pytest.mark.anyio
async def test_with_progress_tracking_no_reporter():
    """Test the progress tracking decorator without progress reporter."""
    
    class MockTask:
        def __init__(self):
            self.progress_reporter = None
    
    task = MockTask()
    
    @with_progress_tracking("test_step", "Test step description")
    async def test_method(self):
        return "success"
    
    # Should work without error even without progress reporter
    result = await test_method(task)
    assert result == "success"


def test_get_progress_reporter():
    """Test get_progress_reporter function."""
    # With correlation ID
    reporter = get_progress_reporter("test-correlation-id")
    assert isinstance(reporter, ProgressReporter)
    assert reporter.correlation_id == "test-correlation-id"
    
    # Without correlation ID
    reporter = get_progress_reporter(None)
    assert reporter is None


@pytest.mark.anyio
async def test_send_progress_update_failure(mock_session):
    """Test handling of failed progress updates."""
    # Mock failed response
    response = AsyncMock()
    response.status = 500
    mock_session.post.return_value.__aenter__.return_value = response
    
    reporter = ProgressReporter("test-correlation-id")
    reporter.session = mock_session
    
    result = await reporter._send_progress_update("test_event", {"data": "test"})
    assert result is False


@pytest.mark.anyio
async def test_send_progress_update_exception():
    """Test handling of exceptions in progress updates."""
    reporter = ProgressReporter("test-correlation-id")
    reporter.session = None  # No session to trigger exception
    
    result = await reporter._send_progress_update("test_event", {"data": "test"})
    assert result is False