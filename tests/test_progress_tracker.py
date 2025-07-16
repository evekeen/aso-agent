"""Unit tests for progress tracker service."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from lib.progress_tracker import (
    ProgressTracker, 
    ProgressEvent, 
    ProgressEventType, 
    TaskProgress,
    NodeProgress,
    get_progress_tracker,
    shutdown_progress_tracker
)


@pytest.fixture
async def tracker():
    """Create a fresh progress tracker for each test."""
    tracker = ProgressTracker(cleanup_ttl_seconds=1)  # Short TTL for testing
    yield tracker
    await tracker.stop_cleanup_task()


@pytest.mark.anyio
async def test_start_task(tracker):
    """Test starting a new task."""
    correlation_id = "test-123"
    task_name = "Test Task"
    
    returned_id = await tracker.start_task(correlation_id, task_name)
    assert returned_id == correlation_id
    
    task = await tracker.get_task_progress(correlation_id)
    assert task is not None
    assert task.correlation_id == correlation_id
    assert task.task_name == task_name
    assert task.status == "running"
    assert len(task.events) == 1
    assert task.events[0].event_type == ProgressEventType.START


@pytest.mark.anyio
async def test_update_progress(tracker):
    """Test updating task progress."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    
    await tracker.update_progress(
        correlation_id=correlation_id,
        node_name="test_node",
        current_operation="Testing operation",
        progress_percentage=50.0,
        metadata={"key": "value"}
    )
    
    task = await tracker.get_task_progress(correlation_id)
    assert task.current_node == "test_node"
    assert task.current_operation == "Testing operation"
    assert task.overall_progress == 50.0
    assert task.elapsed_time > 0
    assert len(task.events) == 2
    assert task.events[1].event_type == ProgressEventType.UPDATE
    assert task.events[1].metadata == {"key": "value"}


@pytest.mark.anyio
async def test_update_sub_task_progress(tracker):
    """Test updating sub-task progress."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    
    await tracker.update_sub_task_progress(
        correlation_id=correlation_id,
        sub_task_name="sub_task_1",
        progress_percentage=75.0,
        current_operation="Processing sub-task",
        node_name="sub_node"
    )
    
    task = await tracker.get_task_progress(correlation_id)
    assert "sub_task_1" in task.sub_tasks
    assert task.sub_tasks["sub_task_1"] == 75.0
    assert len(task.events) == 2
    assert task.events[1].event_type == ProgressEventType.SUB_TASK_UPDATE
    assert task.events[1].metadata["sub_task"] == "sub_task_1"


@pytest.mark.anyio
async def test_report_error(tracker):
    """Test reporting an error."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    
    await tracker.report_error(
        correlation_id=correlation_id,
        node_name="failing_node",
        error_message="Something went wrong",
        error_type="connection_error",
        retry_count=2,
        recovery_action="Retrying connection"
    )
    
    task = await tracker.get_task_progress(correlation_id)
    assert task.error_count == 1
    assert len(task.events) == 2
    
    error_event = task.events[1]
    assert error_event.event_type == ProgressEventType.ERROR
    assert error_event.error_message == "Something went wrong"
    assert error_event.error_type == "connection_error"
    assert error_event.retry_count == 2
    assert error_event.recovery_action == "Retrying connection"


@pytest.mark.anyio
async def test_complete_task_success(tracker):
    """Test completing a task successfully."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    
    await tracker.complete_task(
        correlation_id=correlation_id,
        success=True,
        final_message="Task completed successfully"
    )
    
    task = await tracker.get_task_progress(correlation_id)
    assert task.status == "completed"
    assert task.overall_progress == 100.0
    assert len(task.events) == 2
    assert task.events[1].event_type == ProgressEventType.COMPLETION
    assert task.events[1].current_operation == "Task completed successfully"


@pytest.mark.anyio
async def test_complete_task_failure(tracker):
    """Test completing a task with failure."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    
    # Update progress before failure
    await tracker.update_progress(correlation_id, "test_node", "Working", 30.0)
    
    await tracker.complete_task(
        correlation_id=correlation_id,
        success=False,
        final_message="Task failed"
    )
    
    task = await tracker.get_task_progress(correlation_id)
    assert task.status == "failed"
    assert task.overall_progress == 30.0  # Should preserve last progress
    assert len(task.events) == 3
    assert task.events[2].event_type == ProgressEventType.COMPLETION


@pytest.mark.anyio
async def test_get_task_events(tracker):
    """Test retrieving task events."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    await tracker.update_progress(correlation_id, "node1", "Operation 1", 25.0)
    await tracker.update_progress(correlation_id, "node2", "Operation 2", 50.0)
    
    events = await tracker.get_task_events(correlation_id)
    assert len(events) == 3
    assert events[0].event_type == ProgressEventType.START
    assert events[1].event_type == ProgressEventType.UPDATE
    assert events[2].event_type == ProgressEventType.UPDATE


@pytest.mark.anyio
async def test_get_all_tasks(tracker):
    """Test retrieving all tasks."""
    id1 = await tracker.start_task("task-1", "Task 1")
    id2 = await tracker.start_task("task-2", "Task 2")
    
    all_tasks = await tracker.get_all_tasks()
    assert len(all_tasks) == 2
    assert id1 in all_tasks
    assert id2 in all_tasks


@pytest.mark.anyio
async def test_cleanup_task(tracker):
    """Test manual task cleanup."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    
    # Task should exist
    task = await tracker.get_task_progress(correlation_id)
    assert task is not None
    
    # Clean up task
    result = await tracker.cleanup_task(correlation_id)
    assert result is True
    
    # Task should be gone
    task = await tracker.get_task_progress(correlation_id)
    assert task is None
    
    # Cleanup non-existent task should return False
    result = await tracker.cleanup_task("non-existent")
    assert result is False


@pytest.mark.anyio
async def test_cleanup_expired_tasks(tracker):
    """Test automatic cleanup of expired tasks."""
    correlation_id = "test-123"
    await tracker.start_task(correlation_id, "Test Task")
    
    # Complete the task
    await tracker.complete_task(correlation_id, success=True)
    
    # Manually set the last_update to be old enough for cleanup
    task = await tracker.get_task_progress(correlation_id)
    task.last_update = datetime.now() - timedelta(seconds=2)
    
    # Run cleanup
    await tracker._cleanup_expired_tasks()
    
    # Task should be cleaned up
    task = await tracker.get_task_progress(correlation_id)
    assert task is None


@pytest.mark.anyio
async def test_get_stats(tracker):
    """Test getting tracker statistics."""
    # Start some tasks
    await tracker.start_task("task-1", "Task 1")
    await tracker.start_task("task-2", "Task 2")
    await tracker.complete_task("task-1", success=True)
    await tracker.complete_task("task-2", success=False)
    
    stats = tracker.get_stats()
    assert stats["total_tasks"] == 2
    assert stats["active_tasks"] == 0
    assert stats["completed_tasks"] == 1
    assert stats["failed_tasks"] == 1
    assert stats["cleanup_ttl_seconds"] == 1


@pytest.mark.anyio
async def test_nonexistent_task_operations(tracker):
    """Test operations on non-existent tasks."""
    correlation_id = "non-existent"
    
    # These operations should not raise errors
    await tracker.update_progress(correlation_id, "node", "op", 50.0)
    await tracker.update_sub_task_progress(correlation_id, "sub", 25.0, "op")
    await tracker.report_error(correlation_id, "node", "error")
    await tracker.complete_task(correlation_id)
    
    # Task should still not exist
    task = await tracker.get_task_progress(correlation_id)
    assert task is None


@pytest.mark.anyio
async def test_global_instance():
    """Test global progress tracker instance."""
    tracker1 = get_progress_tracker()
    tracker2 = get_progress_tracker()
    
    # Should be the same instance
    assert tracker1 is tracker2
    
    # Clean up
    await shutdown_progress_tracker()
    
    # Should get a new instance after shutdown
    tracker3 = get_progress_tracker()
    assert tracker3 is not tracker1


@pytest.mark.anyio
async def test_cleanup_task_background():
    """Test that cleanup task starts automatically."""
    tracker = ProgressTracker()
    
    # Should not have a cleanup task initially
    assert tracker._cleanup_task is None
    
    # Start a task, which should start the cleanup task
    await tracker.start_task("test-123", "Test Task")
    
    # Should now have a cleanup task
    assert tracker._cleanup_task is not None
    assert not tracker._cleanup_task.done()
    
    # Stop the cleanup task
    await tracker.stop_cleanup_task()
    assert tracker._cleanup_task.done()


@pytest.mark.anyio
async def test_start_task_auto_correlation_id(tracker):
    """Test starting a task with auto-generated correlation ID."""
    correlation_id = await tracker.start_task(task_name="Auto Task")
    
    # Should return a valid correlation ID
    assert correlation_id is not None
    assert len(correlation_id) > 0
    
    # Task should exist
    task = await tracker.get_task_progress(correlation_id)
    assert task is not None
    assert task.correlation_id == correlation_id
    assert task.task_name == "Auto Task"


@pytest.mark.anyio
async def test_format_progress_log(tracker):
    """Test formatting progress log messages."""
    correlation_id = "test-format-123"
    message = "Test message"
    
    formatted = tracker.format_progress_log(correlation_id, message)
    assert formatted == "[test-for] Test message"


@pytest.mark.anyio
async def test_start_task_with_workflow_steps(tracker):
    """Test starting a task with custom workflow steps."""
    correlation_id = "test-workflow-123"
    workflow_steps = ["step1", "step2", "step3"]
    
    returned_id = await tracker.start_task(correlation_id, "Test Workflow", workflow_steps)
    assert returned_id == correlation_id
    
    task = await tracker.get_task_progress(correlation_id)
    assert task.workflow_steps == workflow_steps
    assert len(task.node_progress) == 3
    assert "step1" in task.node_progress
    assert "step2" in task.node_progress
    assert "step3" in task.node_progress
    
    # All nodes should be initialized as pending
    for step in workflow_steps:
        assert task.node_progress[step].status == "pending"
        assert task.node_progress[step].progress_percentage == 0.0


@pytest.mark.anyio
async def test_start_and_complete_node(tracker):
    """Test starting and completing a node."""
    correlation_id = await tracker.start_task(task_name="Node Test", workflow_steps=["test_node"])
    
    # Start the node
    await tracker.start_node(correlation_id, "test_node", "Starting test node")
    
    task = await tracker.get_task_progress(correlation_id)
    node = task.node_progress["test_node"]
    assert node.status == "running"
    assert node.start_time is not None
    assert node.current_operation == "Starting test node"
    assert task.current_node == "test_node"
    
    # Complete the node
    await tracker.complete_node(correlation_id, "test_node", success=True)
    
    task = await tracker.get_task_progress(correlation_id)
    node = task.node_progress["test_node"]
    assert node.status == "completed"
    assert node.end_time is not None
    assert node.progress_percentage == 100.0
    assert task.status == "completed"  # Should update overall status
    assert task.overall_progress == 100.0


@pytest.mark.anyio
async def test_update_node_progress(tracker):
    """Test updating node progress."""
    correlation_id = await tracker.start_task(task_name="Node Progress Test", workflow_steps=["test_node"])
    
    # Update node progress
    await tracker.update_node_progress(
        correlation_id, 
        "test_node", 
        50.0, 
        "Halfway through",
        "sub_task_1",
        75.0
    )
    
    task = await tracker.get_task_progress(correlation_id)
    node = task.node_progress["test_node"]
    assert node.progress_percentage == 50.0
    assert node.current_operation == "Halfway through"
    assert node.sub_tasks["sub_task_1"] == 75.0
    assert task.overall_progress == 50.0


@pytest.mark.anyio
async def test_aggregate_microservice_progress(tracker):
    """Test aggregating progress from microservices."""
    correlation_id = await tracker.start_task(task_name="Microservice Test", workflow_steps=["service_node"])
    
    # Simulate microservice progress update
    service_progress = {
        "node_name": "service_node",
        "progress_percentage": 75.0,
        "current_operation": "Processing data",
        "sub_tasks": {
            "processing": 80.0,
            "validation": 70.0
        }
    }
    
    await tracker.aggregate_microservice_progress(correlation_id, "test_service", service_progress)
    
    task = await tracker.get_task_progress(correlation_id)
    node = task.node_progress["service_node"]
    assert node.progress_percentage == 75.0
    assert node.current_operation == "Processing data"
    assert node.sub_tasks["processing"] == 80.0
    assert node.sub_tasks["validation"] == 70.0
    assert node.status == "running"
    assert task.overall_progress == 75.0


@pytest.mark.anyio
async def test_get_aggregated_progress(tracker):
    """Test getting aggregated progress view."""
    workflow_steps = ["step1", "step2", "step3"]
    correlation_id = await tracker.start_task(task_name="Aggregation Test", workflow_steps=workflow_steps)
    
    # Update progress for different steps
    await tracker.start_node(correlation_id, "step1", "Starting step 1")
    await tracker.complete_node(correlation_id, "step1", success=True)
    await tracker.start_node(correlation_id, "step2", "Working on step 2")
    await tracker.update_node_progress(correlation_id, "step2", 60.0, "Progressing step 2")
    
    # Get aggregated progress
    aggregated = await tracker.get_aggregated_progress(correlation_id)
    
    assert aggregated is not None
    assert aggregated["correlation_id"] == correlation_id
    assert aggregated["task_name"] == "Aggregation Test"
    assert aggregated["current_node"] == "step2"
    assert aggregated["current_operation"] == "Progressing step 2"
    assert len(aggregated["workflow_progress"]) == 3
    
    # Check workflow progress details
    step1_progress = next(p for p in aggregated["workflow_progress"] if p["node_name"] == "step1")
    assert step1_progress["status"] == "completed"
    assert step1_progress["progress_percentage"] == 100.0
    
    step2_progress = next(p for p in aggregated["workflow_progress"] if p["node_name"] == "step2")
    assert step2_progress["status"] == "running"
    assert step2_progress["progress_percentage"] == 60.0
    assert step2_progress["current_operation"] == "Progressing step 2"
    
    step3_progress = next(p for p in aggregated["workflow_progress"] if p["node_name"] == "step3")
    assert step3_progress["status"] == "pending"
    assert step3_progress["progress_percentage"] == 0.0


@pytest.mark.anyio
async def test_overall_progress_calculation(tracker):
    """Test overall progress calculation across multiple nodes."""
    workflow_steps = ["step1", "step2", "step3"]
    correlation_id = await tracker.start_task(task_name="Progress Calc Test", workflow_steps=workflow_steps)
    
    # Update progress for different steps
    await tracker.update_node_progress(correlation_id, "step1", 100.0, "Step 1 complete")
    await tracker.update_node_progress(correlation_id, "step2", 50.0, "Step 2 halfway")
    await tracker.update_node_progress(correlation_id, "step3", 0.0, "Step 3 not started")
    
    task = await tracker.get_task_progress(correlation_id)
    # Overall progress should be (100 + 50 + 0) / 3 = 50.0
    assert task.overall_progress == 50.0
    assert task.status == "running"


@pytest.mark.anyio
async def test_failure_handling(tracker):
    """Test handling of node failures."""
    correlation_id = await tracker.start_task(task_name="Failure Test", workflow_steps=["failing_node"])
    
    # Complete node with failure
    await tracker.complete_node(correlation_id, "failing_node", success=False)
    
    task = await tracker.get_task_progress(correlation_id)
    node = task.node_progress["failing_node"]
    assert node.status == "failed"
    assert node.error_count == 1
    assert task.error_count == 1
    assert task.status == "failed"


@pytest.mark.anyio
async def test_microservice_completion(tracker):
    """Test microservice progress completing a node."""
    correlation_id = await tracker.start_task(task_name="Microservice Completion Test", workflow_steps=["service_node"])
    
    # Simulate microservice completing its work
    service_progress = {
        "node_name": "service_node",
        "progress_percentage": 100.0,
        "current_operation": "Completed processing",
        "sub_tasks": {
            "processing": 100.0,
            "validation": 100.0
        }
    }
    
    await tracker.aggregate_microservice_progress(correlation_id, "test_service", service_progress)
    
    task = await tracker.get_task_progress(correlation_id)
    node = task.node_progress["service_node"]
    assert node.status == "completed"
    assert node.progress_percentage == 100.0
    assert node.end_time is not None
    assert task.status == "completed"
    assert task.overall_progress == 100.0