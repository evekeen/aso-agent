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