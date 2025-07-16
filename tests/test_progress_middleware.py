"""Unit tests for progress middleware."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agent.progress_middleware import (
    with_progress_tracking,
    update_sub_task_progress,
    update_node_progress,
    ProgressContext,
    NodeMetadata
)
from lib.progress_tracker import ProgressTracker


@pytest.fixture
def mock_tracker():
    """Create a mock progress tracker."""
    tracker = AsyncMock(spec=ProgressTracker)
    tracker.start_task.return_value = "test-correlation-id"
    tracker.start_node.return_value = None
    tracker.complete_node.return_value = None
    tracker.update_progress.return_value = None
    tracker.update_sub_task_progress.return_value = None
    tracker.report_error.return_value = None
    return tracker


@pytest.fixture
def mock_correlation_id():
    """Mock correlation ID functions."""
    with patch('src.agent.progress_middleware.get_correlation_id') as get_mock, \
         patch('src.agent.progress_middleware.set_correlation_id') as set_mock:
        get_mock.return_value = "test-correlation-id"
        yield get_mock, set_mock


@pytest.mark.anyio
async def test_with_progress_tracking_async_node(mock_tracker, mock_correlation_id):
    """Test progress tracking decorator with async node."""
    get_mock, set_mock = mock_correlation_id
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        @with_progress_tracking("test_node", "Test node description")
        async def test_async_node(state: dict) -> dict:
            return {"result": "success", "processed": True}
        
        # Execute the wrapped function
        result = await test_async_node({"input": "test"})
        
        # Verify the result
        assert result["result"] == "success"
        assert result["processed"] is True
        assert result["correlation_id"] == "test-correlation-id"
        
        # Verify progress tracking calls
        mock_tracker.start_node.assert_called_once_with(
            correlation_id="test-correlation-id",
            node_name="test_node",
            current_operation="Test node description"
        )
        mock_tracker.complete_node.assert_called_once_with(
            correlation_id="test-correlation-id",
            node_name="test_node",
            success=True
        )


@pytest.mark.anyio
async def test_with_progress_tracking_sync_node(mock_tracker, mock_correlation_id):
    """Test progress tracking decorator with sync node."""
    get_mock, set_mock = mock_correlation_id
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        @with_progress_tracking("sync_node", "Sync node description")
        def test_sync_node(state: dict) -> dict:
            return {"result": "sync_success"}
        
        # Execute the wrapped function
        result = test_sync_node({"input": "test"})
        
        # Verify the result
        assert result["result"] == "sync_success"
        assert result["correlation_id"] == "test-correlation-id"
        
        # Verify progress tracking calls
        mock_tracker.start_node.assert_called_once_with(
            correlation_id="test-correlation-id",
            node_name="sync_node",
            current_operation="Sync node description"
        )
        mock_tracker.complete_node.assert_called_once_with(
            correlation_id="test-correlation-id",
            node_name="sync_node",
            success=True
        )


@pytest.mark.anyio
async def test_with_progress_tracking_error_handling(mock_tracker, mock_correlation_id):
    """Test error handling in progress tracking decorator."""
    get_mock, set_mock = mock_correlation_id
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        @with_progress_tracking("failing_node", "Node that fails")
        async def test_failing_node(state: dict) -> dict:
            raise ValueError("Test error")
        
        # Execute the wrapped function and expect exception
        with pytest.raises(ValueError, match="Test error"):
            await test_failing_node({"input": "test"})
        
        # Verify error reporting
        mock_tracker.report_error.assert_called_once_with(
            correlation_id="test-correlation-id",
            node_name="failing_node",
            error_message="Test error",
            error_type="ValueError",
            stack_trace="Test error"
        )
        
        # Verify node completion with failure
        mock_tracker.complete_node.assert_called_once_with(
            correlation_id="test-correlation-id",
            node_name="failing_node",
            success=False
        )


@pytest.mark.anyio
async def test_with_progress_tracking_no_correlation_id(mock_tracker):
    """Test progress tracking when no correlation ID exists."""
    with patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.set_correlation_id') as set_mock, \
         patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        
        @with_progress_tracking("new_task_node", "New task node")
        async def test_new_task_node(state: dict) -> dict:
            return {"result": "new_task"}
        
        # Execute the wrapped function
        result = await test_new_task_node({"input": "test"})
        
        # Verify new task was started
        mock_tracker.start_task.assert_called_once_with(
            task_name="ASO Analysis",
            workflow_steps=[
                "collect_app_ideas",
                "generate_initial_keywords",
                "search_apps_for_keywords",
                "get_keyword_total_market_size",
                "filter_keywords_by_market_size",
                "analyze_keyword_difficulty",
                "generate_final_report"
            ]
        )
        
        # Verify correlation ID was set
        set_mock.assert_called_once_with("test-correlation-id")


@pytest.mark.anyio
async def test_with_progress_tracking_correlation_id_from_state(mock_tracker):
    """Test progress tracking when correlation ID is in state."""
    with patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.set_correlation_id') as set_mock, \
         patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        
        @with_progress_tracking("state_correlation_node", "Node with state correlation")
        async def test_state_correlation_node(state: dict) -> dict:
            return {"result": "state_correlation"}
        
        # Execute with correlation ID in state
        result = await test_state_correlation_node({"correlation_id": "state-correlation-id"})
        
        # Verify correlation ID was set from state
        set_mock.assert_called_once_with("state-correlation-id")
        
        # Verify start_task was NOT called (correlation ID already existed)
        mock_tracker.start_task.assert_not_called()


@pytest.mark.anyio
async def test_update_sub_task_progress(mock_tracker, mock_correlation_id):
    """Test sub-task progress update."""
    get_mock, set_mock = mock_correlation_id
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        # Update sub-task progress
        update_sub_task_progress(
            sub_task_name="subtask_1",
            progress_percentage=75.0,
            current_operation="Processing subtask",
            node_name="parent_node"
        )
        
        # Give asyncio time to process
        await asyncio.sleep(0.01)
        
        # Verify the call
        mock_tracker.update_sub_task_progress.assert_called_once_with(
            correlation_id="test-correlation-id",
            sub_task_name="subtask_1",
            progress_percentage=75.0,
            current_operation="Processing subtask",
            node_name="parent_node"
        )


@pytest.mark.anyio
async def test_update_node_progress(mock_tracker, mock_correlation_id):
    """Test node progress update."""
    get_mock, set_mock = mock_correlation_id
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        # Update node progress
        update_node_progress(
            progress_percentage=50.0,
            current_operation="Processing data",
            node_name="processing_node"
        )
        
        # Give asyncio time to process
        await asyncio.sleep(0.01)
        
        # Verify the call
        mock_tracker.update_progress.assert_called_once_with(
            correlation_id="test-correlation-id",
            node_name="processing_node",
            current_operation="Processing data",
            progress_percentage=50.0
        )


@pytest.mark.anyio
async def test_progress_context():
    """Test ProgressContext for tracking progress within a node."""
    mock_tracker = AsyncMock(spec=ProgressTracker)
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value="context-correlation-id"):
        
        async with ProgressContext("test_node", 10) as ctx:
            # Test update method
            await ctx.update(3, "Processing item 3")
            
            # Test increment method
            await ctx.increment("Processing item 4")
        
        # Verify calls
        assert mock_tracker.update_progress.call_count == 2
        
        # Check first call (update)
        first_call = mock_tracker.update_progress.call_args_list[0]
        assert first_call[1]["correlation_id"] == "context-correlation-id"
        assert first_call[1]["node_name"] == "test_node"
        assert first_call[1]["current_operation"] == "Processing item 3"
        assert first_call[1]["progress_percentage"] == 30.0  # 3/10 * 100
        
        # Check second call (increment)
        second_call = mock_tracker.update_progress.call_args_list[1]
        assert second_call[1]["correlation_id"] == "context-correlation-id"
        assert second_call[1]["node_name"] == "test_node"
        assert second_call[1]["current_operation"] == "Processing item 4"
        assert second_call[1]["progress_percentage"] == 40.0  # 4/10 * 100


@pytest.mark.anyio
async def test_node_metadata():
    """Test NodeMetadata dataclass."""
    metadata = NodeMetadata(
        name="test_node",
        description="Test node description",
        estimated_duration=30.0,
        sub_tasks=["task1", "task2"]
    )
    
    assert metadata.name == "test_node"
    assert metadata.description == "Test node description"
    assert metadata.estimated_duration == 30.0
    assert metadata.sub_tasks == ["task1", "task2"]


@pytest.mark.anyio
async def test_with_progress_tracking_with_config(mock_tracker, mock_correlation_id):
    """Test progress tracking decorator with config parameter."""
    get_mock, set_mock = mock_correlation_id
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        @with_progress_tracking("config_node", "Node with config")
        async def test_config_node(state: dict, config: dict) -> dict:
            return {"result": "config_success", "config_used": config is not None}
        
        # Execute with config
        result = await test_config_node({"input": "test"}, {"thread_id": "test-thread"})
        
        # Verify the result
        assert result["result"] == "config_success"
        assert result["config_used"] is True
        assert result["correlation_id"] == "test-correlation-id"


@pytest.mark.anyio
async def test_update_functions_no_correlation_id(mock_tracker):
    """Test update functions when no correlation ID is available."""
    with patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker):
        
        # These should not raise errors even without correlation ID
        update_sub_task_progress("subtask", 50.0, "operation")
        update_node_progress(75.0, "operation")
        
        # Give asyncio time to process
        await asyncio.sleep(0.01)
        
        # Verify no calls were made
        mock_tracker.update_sub_task_progress.assert_not_called()
        mock_tracker.update_progress.assert_not_called()


def test_decorator_metadata_extraction():
    """Test that decorator properly extracts metadata."""
    @with_progress_tracking(
        "metadata_node",
        "Node with metadata",
        estimated_duration=60.0,
        sub_tasks=["sub1", "sub2", "sub3"]
    )
    def test_metadata_node(state: dict) -> dict:
        return {"result": "metadata"}
    
    # The metadata should be stored in the wrapper
    # This is more of a structural test to ensure the decorator works
    assert callable(test_metadata_node)
    
    # Test that the function can be called
    result = test_metadata_node({"input": "test"})
    assert "result" in result