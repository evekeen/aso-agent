"""Unit tests for progress data models."""

import pytest
from datetime import datetime
from lib.progress_models import (
    ProgressStatus,
    ProgressEventType,
    WorkflowStartEvent,
    WorkflowCompletionEvent,
    NodeStartEvent,
    NodeUpdateEvent,
    NodeCompletionEvent,
    SubTaskStartEvent,
    SubTaskUpdateEvent,
    SubTaskCompletionEvent,
    ErrorEvent,
    RetryEvent,
    MicroserviceUpdateEvent,
    ProgressSummary,
    ProgressTimeline,
    deserialize_event,
    serialize_event,
    EVENT_TYPE_MAP
)


def test_progress_status_enum():
    """Test ProgressStatus enum values."""
    assert ProgressStatus.PENDING.value == "pending"
    assert ProgressStatus.RUNNING.value == "running"
    assert ProgressStatus.COMPLETED.value == "completed"
    assert ProgressStatus.FAILED.value == "failed"
    assert ProgressStatus.CANCELLED.value == "cancelled"


def test_progress_event_type_enum():
    """Test ProgressEventType enum values."""
    assert ProgressEventType.WORKFLOW_START.value == "workflow_start"
    assert ProgressEventType.NODE_UPDATE.value == "node_update"
    assert ProgressEventType.ERROR.value == "error"
    assert ProgressEventType.MICROSERVICE_UPDATE.value == "microservice_update"


def test_workflow_start_event():
    """Test WorkflowStartEvent creation and serialization."""
    event = WorkflowStartEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        task_name="Test Workflow",
        workflow_steps=["step1", "step2", "step3"],
        estimated_duration=300.0,
        elapsed_time=0.0,
        metadata={"key": "value"}
    )
    
    assert event.event_type == ProgressEventType.WORKFLOW_START
    assert event.task_name == "Test Workflow"
    assert event.workflow_steps == ["step1", "step2", "step3"]
    assert event.estimated_duration == 300.0
    
    # Test serialization
    data = event.to_dict()
    assert data["event_type"] == "workflow_start"
    assert data["task_name"] == "Test Workflow"
    assert data["workflow_steps"] == ["step1", "step2", "step3"]
    assert data["estimated_duration"] == 300.0
    
    # Test deserialization
    restored_event = WorkflowStartEvent.from_dict(data)
    assert restored_event.correlation_id == event.correlation_id
    assert restored_event.task_name == event.task_name
    assert restored_event.workflow_steps == event.workflow_steps
    assert restored_event.estimated_duration == event.estimated_duration


def test_workflow_completion_event():
    """Test WorkflowCompletionEvent creation and serialization."""
    event = WorkflowCompletionEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 5, 0),
        task_name="Test Workflow",
        status=ProgressStatus.COMPLETED,
        final_progress=100.0,
        total_duration=300.0,
        error_count=2,
        summary="Workflow completed successfully"
    )
    
    assert event.event_type == ProgressEventType.WORKFLOW_COMPLETION
    assert event.status == ProgressStatus.COMPLETED
    assert event.final_progress == 100.0
    assert event.total_duration == 300.0
    assert event.error_count == 2
    
    # Test serialization
    data = event.to_dict()
    assert data["status"] == "completed"
    assert data["final_progress"] == 100.0
    assert data["summary"] == "Workflow completed successfully"
    
    # Test deserialization
    restored_event = WorkflowCompletionEvent.from_dict(data)
    assert restored_event.status == ProgressStatus.COMPLETED
    assert restored_event.final_progress == 100.0
    assert restored_event.summary == "Workflow completed successfully"


def test_node_start_event():
    """Test NodeStartEvent creation and serialization."""
    event = NodeStartEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 1, 0),
        node_name="test_node",
        current_operation="Starting test node",
        estimated_duration=60.0
    )
    
    assert event.event_type == ProgressEventType.NODE_START
    assert event.node_name == "test_node"
    assert event.current_operation == "Starting test node"
    assert event.estimated_duration == 60.0
    
    # Test serialization and deserialization
    data = event.to_dict()
    restored_event = NodeStartEvent.from_dict(data)
    assert restored_event.node_name == event.node_name
    assert restored_event.current_operation == event.current_operation
    assert restored_event.estimated_duration == event.estimated_duration


def test_node_update_event():
    """Test NodeUpdateEvent creation and serialization."""
    event = NodeUpdateEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 2, 0),
        node_name="test_node",
        current_operation="Processing data",
        progress_percentage=50.0,
        status=ProgressStatus.RUNNING
    )
    
    assert event.event_type == ProgressEventType.NODE_UPDATE
    assert event.progress_percentage == 50.0
    assert event.status == ProgressStatus.RUNNING
    
    # Test serialization and deserialization
    data = event.to_dict()
    assert data["status"] == "running"
    restored_event = NodeUpdateEvent.from_dict(data)
    assert restored_event.progress_percentage == 50.0
    assert restored_event.status == ProgressStatus.RUNNING


def test_node_completion_event():
    """Test NodeCompletionEvent creation and serialization."""
    event = NodeCompletionEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 3, 0),
        node_name="test_node",
        status=ProgressStatus.COMPLETED,
        final_progress=100.0,
        duration=120.0,
        result_summary="Node completed successfully"
    )
    
    assert event.event_type == ProgressEventType.NODE_COMPLETION
    assert event.status == ProgressStatus.COMPLETED
    assert event.final_progress == 100.0
    assert event.duration == 120.0
    
    # Test serialization and deserialization
    data = event.to_dict()
    restored_event = NodeCompletionEvent.from_dict(data)
    assert restored_event.status == ProgressStatus.COMPLETED
    assert restored_event.final_progress == 100.0
    assert restored_event.result_summary == "Node completed successfully"


def test_sub_task_events():
    """Test SubTask event creation and serialization."""
    # Start event
    start_event = SubTaskStartEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 1, 30),
        node_name="test_node",
        sub_task_name="subtask_1",
        current_operation="Starting subtask",
        estimated_duration=30.0
    )
    
    assert start_event.event_type == ProgressEventType.SUB_TASK_START
    assert start_event.sub_task_name == "subtask_1"
    
    # Update event
    update_event = SubTaskUpdateEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 2, 0),
        node_name="test_node",
        sub_task_name="subtask_1",
        current_operation="Processing subtask",
        progress_percentage=75.0,
        status=ProgressStatus.RUNNING
    )
    
    assert update_event.event_type == ProgressEventType.SUB_TASK_UPDATE
    assert update_event.progress_percentage == 75.0
    
    # Completion event
    completion_event = SubTaskCompletionEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 2, 30),
        node_name="test_node",
        sub_task_name="subtask_1",
        status=ProgressStatus.COMPLETED,
        final_progress=100.0,
        duration=60.0,
        result_summary="Subtask completed"
    )
    
    assert completion_event.event_type == ProgressEventType.SUB_TASK_COMPLETION
    assert completion_event.status == ProgressStatus.COMPLETED
    
    # Test serialization and deserialization
    for event in [start_event, update_event, completion_event]:
        data = event.to_dict()
        restored_event = event.__class__.from_dict(data)
        assert restored_event.sub_task_name == event.sub_task_name
        assert restored_event.node_name == event.node_name


def test_error_event():
    """Test ErrorEvent creation and serialization."""
    event = ErrorEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 2, 15),
        node_name="failing_node",
        error_type="ConnectionError",
        error_message="Failed to connect to service",
        retry_count=2,
        recovery_action="Retrying with backoff",
        stack_trace="Traceback (most recent call last)..."
    )
    
    assert event.event_type == ProgressEventType.ERROR
    assert event.error_type == "ConnectionError"
    assert event.error_message == "Failed to connect to service"
    assert event.retry_count == 2
    assert event.recovery_action == "Retrying with backoff"
    
    # Test serialization and deserialization
    data = event.to_dict()
    restored_event = ErrorEvent.from_dict(data)
    assert restored_event.error_type == "ConnectionError"
    assert restored_event.error_message == "Failed to connect to service"
    assert restored_event.retry_count == 2
    assert restored_event.stack_trace == "Traceback (most recent call last)..."


def test_retry_event():
    """Test RetryEvent creation and serialization."""
    event = RetryEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 2, 20),
        node_name="retrying_node",
        retry_count=3,
        max_retries=5,
        retry_reason="Network timeout",
        retry_delay=5.0
    )
    
    assert event.event_type == ProgressEventType.RETRY
    assert event.retry_count == 3
    assert event.max_retries == 5
    assert event.retry_reason == "Network timeout"
    assert event.retry_delay == 5.0
    
    # Test serialization and deserialization
    data = event.to_dict()
    restored_event = RetryEvent.from_dict(data)
    assert restored_event.retry_count == 3
    assert restored_event.max_retries == 5
    assert restored_event.retry_reason == "Network timeout"
    assert restored_event.retry_delay == 5.0


def test_microservice_update_event():
    """Test MicroserviceUpdateEvent creation and serialization."""
    event = MicroserviceUpdateEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 3, 0),
        service_name="playwright_service",
        node_name="analyze_keyword_difficulty",
        current_operation="Processing keywords",
        progress_percentage=60.0,
        status=ProgressStatus.RUNNING,
        sub_tasks={"keyword_1": 100.0, "keyword_2": 50.0, "keyword_3": 25.0}
    )
    
    assert event.event_type == ProgressEventType.MICROSERVICE_UPDATE
    assert event.service_name == "playwright_service"
    assert event.node_name == "analyze_keyword_difficulty"
    assert event.progress_percentage == 60.0
    assert event.status == ProgressStatus.RUNNING
    assert event.sub_tasks["keyword_1"] == 100.0
    
    # Test serialization and deserialization
    data = event.to_dict()
    restored_event = MicroserviceUpdateEvent.from_dict(data)
    assert restored_event.service_name == "playwright_service"
    assert restored_event.progress_percentage == 60.0
    assert restored_event.status == ProgressStatus.RUNNING
    assert restored_event.sub_tasks["keyword_1"] == 100.0


def test_event_serialization_deserialization():
    """Test generic event serialization and deserialization."""
    events = [
        WorkflowStartEvent(
            correlation_id="test-123",
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            task_name="Test",
            workflow_steps=["step1"]
        ),
        NodeUpdateEvent(
            correlation_id="test-123",
            timestamp=datetime(2023, 1, 1, 12, 1, 0),
            node_name="test_node",
            current_operation="Testing",
            progress_percentage=50.0,
            status=ProgressStatus.RUNNING
        ),
        ErrorEvent(
            correlation_id="test-123",
            timestamp=datetime(2023, 1, 1, 12, 2, 0),
            node_name="failing_node",
            error_type="TestError",
            error_message="Test error message"
        )
    ]
    
    for event in events:
        # Test serialize_event function
        data = serialize_event(event)
        assert data["event_type"] == event.event_type.value
        assert data["correlation_id"] == event.correlation_id
        
        # Test deserialize_event function
        restored_event = deserialize_event(data)
        assert restored_event.event_type == event.event_type
        assert restored_event.correlation_id == event.correlation_id
        assert type(restored_event) == type(event)


def test_progress_summary():
    """Test ProgressSummary creation and serialization."""
    summary = ProgressSummary(
        correlation_id="test-123",
        name="Test Node",
        status=ProgressStatus.COMPLETED,
        progress_percentage=100.0,
        start_time=datetime(2023, 1, 1, 12, 0, 0),
        end_time=datetime(2023, 1, 1, 12, 2, 0),
        duration=120.0,
        error_count=1,
        last_operation="Completed successfully",
        sub_tasks={"task1": 100.0, "task2": 100.0}
    )
    
    assert summary.status == ProgressStatus.COMPLETED
    assert summary.progress_percentage == 100.0
    assert summary.duration == 120.0
    assert summary.error_count == 1
    assert summary.sub_tasks["task1"] == 100.0
    
    # Test serialization
    data = summary.to_dict()
    assert data["status"] == "completed"
    assert data["progress_percentage"] == 100.0
    assert data["duration"] == 120.0
    assert data["error_count"] == 1
    assert data["sub_tasks"]["task1"] == 100.0


def test_progress_timeline():
    """Test ProgressTimeline creation and functionality."""
    timeline = ProgressTimeline(
        correlation_id="test-123",
        task_name="Test Timeline"
    )
    
    # Add events
    start_event = WorkflowStartEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        task_name="Test",
        workflow_steps=["step1"]
    )
    
    node_event = NodeUpdateEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 1, 0),
        node_name="test_node",
        current_operation="Testing",
        progress_percentage=50.0,
        status=ProgressStatus.RUNNING
    )
    
    error_event = ErrorEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 2, 0),
        node_name="test_node",
        error_type="TestError",
        error_message="Test error"
    )
    
    timeline.add_event(start_event)
    timeline.add_event(node_event)
    timeline.add_event(error_event)
    
    assert len(timeline.events) == 3
    
    # Test get_events_by_type
    workflow_events = timeline.get_events_by_type(ProgressEventType.WORKFLOW_START)
    assert len(workflow_events) == 1
    assert workflow_events[0] == start_event
    
    error_events = timeline.get_events_by_type(ProgressEventType.ERROR)
    assert len(error_events) == 1
    assert error_events[0] == error_event
    
    # Test get_events_by_node
    node_events = timeline.get_events_by_node("test_node")
    assert len(node_events) == 2
    assert node_event in node_events
    assert error_event in node_events
    
    # Test serialization
    data = timeline.to_dict()
    assert data["correlation_id"] == "test-123"
    assert data["task_name"] == "Test Timeline"
    assert len(data["events"]) == 3


def test_event_type_map():
    """Test EVENT_TYPE_MAP completeness."""
    # Ensure all event types are mapped
    for event_type in ProgressEventType:
        assert event_type in EVENT_TYPE_MAP
        event_class = EVENT_TYPE_MAP[event_type]
        assert hasattr(event_class, 'from_dict')
        assert hasattr(event_class, 'to_dict')


def test_event_metadata():
    """Test event metadata handling."""
    metadata = {
        "custom_field": "custom_value",
        "numbers": [1, 2, 3],
        "nested": {"key": "value"}
    }
    
    event = NodeUpdateEvent(
        correlation_id="test-123",
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        node_name="test_node",
        current_operation="Testing metadata",
        progress_percentage=25.0,
        status=ProgressStatus.RUNNING,
        metadata=metadata
    )
    
    assert event.metadata == metadata
    
    # Test serialization preserves metadata
    data = event.to_dict()
    assert data["metadata"] == metadata
    
    # Test deserialization preserves metadata
    restored_event = NodeUpdateEvent.from_dict(data)
    assert restored_event.metadata == metadata