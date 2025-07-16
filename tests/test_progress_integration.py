"""Integration tests for progress tracking in LangGraph workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from lib.progress_tracker import ProgressTracker
from src.agent.progress_middleware import with_progress_tracking
from src.agent.graph import collect_app_ideas, generate_initial_keywords


@pytest.fixture
def mock_tracker():
    """Create a mock progress tracker."""
    tracker = AsyncMock(spec=ProgressTracker)
    tracker.start_task.return_value = "integration-test-id"
    tracker.start_node.return_value = None
    tracker.complete_node.return_value = None
    tracker.update_progress.return_value = None
    tracker.get_task_progress.return_value = None
    return tracker


@pytest.mark.anyio
async def test_collect_app_ideas_with_progress_tracking(mock_tracker):
    """Test that collect_app_ideas node has progress tracking."""
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.set_correlation_id'):
        
        # Execute the node
        result = collect_app_ideas({"input": "test"})
        
        # Verify the result
        assert "ideas" in result
        assert result["ideas"] == ["golf shot tracer", "snoring tracker"]
        assert result["correlation_id"] == "integration-test-id"
        
        # Verify progress tracking was called
        mock_tracker.start_task.assert_called_once()
        mock_tracker.start_node.assert_called_once_with(
            correlation_id="integration-test-id",
            node_name="collect_app_ideas",
            current_operation="Collecting app ideas for ASO analysis"
        )
        mock_tracker.complete_node.assert_called_once_with(
            correlation_id="integration-test-id",
            node_name="collect_app_ideas",
            success=True
        )


@pytest.mark.anyio
async def test_generate_initial_keywords_with_progress_tracking(mock_tracker):
    """Test that generate_initial_keywords node has progress tracking."""
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value="existing-correlation-id"), \
         patch('src.agent.progress_middleware.set_correlation_id'), \
         patch('src.agent.graph.generate_keywords', return_value={"idea1": ["keyword1", "keyword2"]}):
        
        # Execute the node
        result = generate_initial_keywords({"ideas": ["idea1"]})
        
        # Verify the result
        assert "initial_keywords" in result
        assert result["initial_keywords"] == {"idea1": ["keyword1", "keyword2"]}
        assert result["correlation_id"] == "existing-correlation-id"
        
        # Verify progress tracking was called
        mock_tracker.start_task.assert_not_called()  # Should not start new task
        mock_tracker.start_node.assert_called_once_with(
            correlation_id="existing-correlation-id",
            node_name="generate_initial_keywords",
            current_operation="Generating initial keywords using LLM"
        )
        mock_tracker.complete_node.assert_called_once_with(
            correlation_id="existing-correlation-id",
            node_name="generate_initial_keywords",
            success=True
        )
        
        # Verify progress updates were called
        assert mock_tracker.update_progress.call_count == 2


@pytest.mark.anyio
async def test_node_error_handling_with_progress_tracking(mock_tracker):
    """Test error handling in progress-tracked nodes."""
    
    # Create a test async node that will fail
    @with_progress_tracking("test_error_node", "Test error node")
    async def test_error_node(state: dict) -> dict:
        raise RuntimeError("Test error")
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value="error-test-id"), \
         patch('src.agent.progress_middleware.set_correlation_id'):
        
        # Execute the node and expect error
        with pytest.raises(RuntimeError, match="Test error"):
            await test_error_node({"ideas": ["idea1"]})
        
        # Verify error was reported
        mock_tracker.report_error.assert_called_once_with(
            correlation_id="error-test-id",
            node_name="test_error_node",
            error_message="Test error",
            error_type="RuntimeError",
            stack_trace="Test error"
        )
        
        # Verify node was completed with failure
        mock_tracker.complete_node.assert_called_once_with(
            correlation_id="error-test-id",
            node_name="test_error_node",
            success=False
        )


@pytest.mark.anyio
async def test_correlation_id_propagation_through_workflow():
    """Test that correlation ID is properly propagated through workflow state."""
    
    # Create a simple workflow with multiple nodes
    @with_progress_tracking("test_node_1", "First test node")
    def test_node_1(state: dict) -> dict:
        return {"step1_complete": True}
    
    @with_progress_tracking("test_node_2", "Second test node")
    def test_node_2(state: dict) -> dict:
        return {"step2_complete": True}
    
    mock_tracker = AsyncMock(spec=ProgressTracker)
    mock_tracker.start_task.return_value = "workflow-correlation-id"
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.set_correlation_id') as set_correlation_mock:
        
        # Execute first node
        result1 = test_node_1({"initial": "data"})
        
        # Verify correlation ID was set and added to result
        assert result1["correlation_id"] == "workflow-correlation-id"
        set_correlation_mock.assert_called_with("workflow-correlation-id")
        
        # Mock that correlation ID is now available for second node
        with patch('src.agent.progress_middleware.get_correlation_id', return_value="workflow-correlation-id"):
            # Execute second node with state from first node
            result2 = test_node_2(result1)
            
            # Verify correlation ID is maintained
            assert result2["correlation_id"] == "workflow-correlation-id"
            
            # Verify both nodes used the same correlation ID
            start_node_calls = mock_tracker.start_node.call_args_list
            assert len(start_node_calls) == 2
            assert start_node_calls[0][1]["correlation_id"] == "workflow-correlation-id"
            assert start_node_calls[1][1]["correlation_id"] == "workflow-correlation-id"


@pytest.mark.anyio
async def test_workflow_step_tracking():
    """Test that workflow steps are properly tracked."""
    mock_tracker = AsyncMock(spec=ProgressTracker)
    mock_tracker.start_task.return_value = "workflow-steps-id"
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.set_correlation_id'):
        
        # Execute a node to trigger workflow creation
        result = collect_app_ideas({"input": "test"})
        
        # Verify start_task was called with the correct workflow steps
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


@pytest.mark.anyio
async def test_concurrent_node_execution():
    """Test that multiple nodes can execute concurrently without correlation ID conflicts."""
    mock_tracker = AsyncMock(spec=ProgressTracker)
    mock_tracker.start_task.side_effect = ["correlation-1", "correlation-2"]
    
    @with_progress_tracking("concurrent_node", "Concurrent test node")
    def concurrent_test_node(state: dict) -> dict:
        return {"result": state.get("input", "default")}
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.set_correlation_id'):
        
        # Execute nodes concurrently
        async def run_node_1():
            return concurrent_test_node({"input": "task1"})
        
        async def run_node_2():
            return concurrent_test_node({"input": "task2"})
        
        results = await asyncio.gather(
            asyncio.create_task(run_node_1()),
            asyncio.create_task(run_node_2())
        )
        
        # Verify both tasks completed successfully
        assert len(results) == 2
        assert results[0]["correlation_id"] in ["correlation-1", "correlation-2"]
        assert results[1]["correlation_id"] in ["correlation-1", "correlation-2"]
        
        # Verify separate tasks were started
        assert mock_tracker.start_task.call_count == 2


def test_node_metadata_preservation():
    """Test that node metadata is preserved in the decorator."""
    @with_progress_tracking("metadata_node", "Node with metadata", estimated_duration=60.0)
    def metadata_test_node(state: dict) -> dict:
        """Test node with metadata."""
        return {"metadata": "preserved"}
    
    # Verify function metadata is preserved
    assert metadata_test_node.__name__ == "metadata_test_node"
    assert "Test node with metadata" in metadata_test_node.__doc__
    assert callable(metadata_test_node)


@pytest.mark.anyio
async def test_async_node_compatibility():
    """Test that async nodes work correctly with progress tracking."""
    @with_progress_tracking("async_test_node", "Async test node")
    async def async_test_node(state: dict) -> dict:
        await asyncio.sleep(0.001)  # Simulate async work
        return {"async_result": "success"}
    
    mock_tracker = AsyncMock(spec=ProgressTracker)
    mock_tracker.start_task.return_value = "async-correlation-id"
    
    with patch('src.agent.progress_middleware.get_progress_tracker', return_value=mock_tracker), \
         patch('src.agent.progress_middleware.get_correlation_id', return_value=None), \
         patch('src.agent.progress_middleware.set_correlation_id'):
        
        # Execute async node
        result = await async_test_node({"input": "async_test"})
        
        # Verify the result
        assert result["async_result"] == "success"
        assert result["correlation_id"] == "async-correlation-id"
        
        # Verify progress tracking was called
        mock_tracker.start_node.assert_called_once()
        mock_tracker.complete_node.assert_called_once_with(
            correlation_id="async-correlation-id",
            node_name="async_test_node",
            success=True
        )