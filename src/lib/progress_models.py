"""Progress data models for different event types in ASO analysis workflows."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod


class ProgressStatus(Enum):
    """Status values for progress tracking."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressEventType(Enum):
    """Types of progress events."""
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETION = "workflow_completion"
    NODE_START = "node_start"
    NODE_UPDATE = "node_update"
    NODE_COMPLETION = "node_completion"
    SUB_TASK_START = "sub_task_start"
    SUB_TASK_UPDATE = "sub_task_update"
    SUB_TASK_COMPLETION = "sub_task_completion"
    ERROR = "error"
    RETRY = "retry"
    MICROSERVICE_UPDATE = "microservice_update"


@dataclass
class WorkflowStartEvent:
    """Event for workflow start."""
    correlation_id: str
    timestamp: datetime
    task_name: str
    workflow_steps: List[str]
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: Optional[float] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.WORKFLOW_START
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "task_name": self.task_name,
            "workflow_steps": self.workflow_steps,
            "estimated_duration": self.estimated_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStartEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            task_name=data["task_name"],
            workflow_steps=data["workflow_steps"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            estimated_duration=data.get("estimated_duration")
        )


@dataclass
class WorkflowCompletionEvent:
    """Event for workflow completion."""
    correlation_id: str
    timestamp: datetime
    task_name: str
    status: ProgressStatus
    final_progress: float
    total_duration: float
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_count: int = field(default=0)
    summary: Optional[str] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.WORKFLOW_COMPLETION
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "task_name": self.task_name,
            "status": self.status.value,
            "final_progress": self.final_progress,
            "total_duration": self.total_duration,
            "error_count": self.error_count,
            "summary": self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowCompletionEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            task_name=data["task_name"],
            status=ProgressStatus(data["status"]),
            final_progress=data["final_progress"],
            total_duration=data["total_duration"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            error_count=data.get("error_count", 0),
            summary=data.get("summary")
        )


@dataclass
class NodeStartEvent:
    """Event for node start."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    current_operation: str
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: Optional[float] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.NODE_START
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "current_operation": self.current_operation,
            "estimated_duration": self.estimated_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeStartEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            current_operation=data["current_operation"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            estimated_duration=data.get("estimated_duration")
        )


@dataclass
class NodeUpdateEvent:
    """Event for node progress update."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    current_operation: str
    progress_percentage: float
    status: ProgressStatus
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.NODE_UPDATE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "current_operation": self.current_operation,
            "progress_percentage": self.progress_percentage,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeUpdateEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            current_operation=data["current_operation"],
            progress_percentage=data["progress_percentage"],
            status=ProgressStatus(data["status"]),
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class NodeCompletionEvent:
    """Event for node completion."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    status: ProgressStatus
    final_progress: float
    duration: float
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    result_summary: Optional[str] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.NODE_COMPLETION
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "status": self.status.value,
            "final_progress": self.final_progress,
            "duration": self.duration,
            "result_summary": self.result_summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeCompletionEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            status=ProgressStatus(data["status"]),
            final_progress=data["final_progress"],
            duration=data["duration"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            result_summary=data.get("result_summary")
        )


@dataclass
class SubTaskStartEvent:
    """Event for sub-task start."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    sub_task_name: str
    current_operation: str
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: Optional[float] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.SUB_TASK_START
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "sub_task_name": self.sub_task_name,
            "current_operation": self.current_operation,
            "estimated_duration": self.estimated_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubTaskStartEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            sub_task_name=data["sub_task_name"],
            current_operation=data["current_operation"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            estimated_duration=data.get("estimated_duration")
        )


@dataclass
class SubTaskUpdateEvent:
    """Event for sub-task progress update."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    sub_task_name: str
    current_operation: str
    progress_percentage: float
    status: ProgressStatus
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.SUB_TASK_UPDATE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "sub_task_name": self.sub_task_name,
            "current_operation": self.current_operation,
            "progress_percentage": self.progress_percentage,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubTaskUpdateEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            sub_task_name=data["sub_task_name"],
            current_operation=data["current_operation"],
            progress_percentage=data["progress_percentage"],
            status=ProgressStatus(data["status"]),
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class SubTaskCompletionEvent:
    """Event for sub-task completion."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    sub_task_name: str
    status: ProgressStatus
    final_progress: float
    duration: float
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    result_summary: Optional[str] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.SUB_TASK_COMPLETION
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "sub_task_name": self.sub_task_name,
            "status": self.status.value,
            "final_progress": self.final_progress,
            "duration": self.duration,
            "result_summary": self.result_summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubTaskCompletionEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            sub_task_name=data["sub_task_name"],
            status=ProgressStatus(data["status"]),
            final_progress=data["final_progress"],
            duration=data["duration"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            result_summary=data.get("result_summary")
        )


@dataclass
class ErrorEvent:
    """Event for error occurrence."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    error_type: str
    error_message: str
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = field(default=0)
    recovery_action: Optional[str] = field(default=None)
    stack_trace: Optional[str] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "recovery_action": self.recovery_action,
            "stack_trace": self.stack_trace
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            error_type=data["error_type"],
            error_message=data["error_message"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            retry_count=data.get("retry_count", 0),
            recovery_action=data.get("recovery_action"),
            stack_trace=data.get("stack_trace")
        )


@dataclass
class RetryEvent:
    """Event for retry attempt."""
    correlation_id: str
    timestamp: datetime
    node_name: str
    retry_count: int
    max_retries: int
    retry_reason: str
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_delay: Optional[float] = field(default=None)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.RETRY
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "node_name": self.node_name,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "retry_reason": self.retry_reason,
            "retry_delay": self.retry_delay
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            node_name=data["node_name"],
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            retry_reason=data["retry_reason"],
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            retry_delay=data.get("retry_delay")
        )


@dataclass
class MicroserviceUpdateEvent:
    """Event for microservice progress update."""
    correlation_id: str
    timestamp: datetime
    service_name: str
    node_name: str
    current_operation: str
    progress_percentage: float
    status: ProgressStatus
    elapsed_time: float = field(default=0.0)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sub_tasks: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        self.event_type = ProgressEventType.MICROSERVICE_UPDATE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata,
            "service_name": self.service_name,
            "node_name": self.node_name,
            "current_operation": self.current_operation,
            "progress_percentage": self.progress_percentage,
            "status": self.status.value,
            "sub_tasks": self.sub_tasks
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MicroserviceUpdateEvent':
        return cls(
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            service_name=data["service_name"],
            node_name=data["node_name"],
            current_operation=data["current_operation"],
            progress_percentage=data["progress_percentage"],
            status=ProgressStatus(data["status"]),
            elapsed_time=data.get("elapsed_time", 0.0),
            metadata=data.get("metadata", {}),
            sub_tasks=data.get("sub_tasks", {})
        )


# Event type mapping for deserialization
EVENT_TYPE_MAP = {
    ProgressEventType.WORKFLOW_START: WorkflowStartEvent,
    ProgressEventType.WORKFLOW_COMPLETION: WorkflowCompletionEvent,
    ProgressEventType.NODE_START: NodeStartEvent,
    ProgressEventType.NODE_UPDATE: NodeUpdateEvent,
    ProgressEventType.NODE_COMPLETION: NodeCompletionEvent,
    ProgressEventType.SUB_TASK_START: SubTaskStartEvent,
    ProgressEventType.SUB_TASK_UPDATE: SubTaskUpdateEvent,
    ProgressEventType.SUB_TASK_COMPLETION: SubTaskCompletionEvent,
    ProgressEventType.ERROR: ErrorEvent,
    ProgressEventType.RETRY: RetryEvent,
    ProgressEventType.MICROSERVICE_UPDATE: MicroserviceUpdateEvent
}


# Type alias for all event types
ProgressEvent = Union[
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
    MicroserviceUpdateEvent
]


def deserialize_event(data: Dict[str, Any]) -> ProgressEvent:
    """Deserialize event from dictionary."""
    event_type = ProgressEventType(data["event_type"])
    event_class = EVENT_TYPE_MAP[event_type]
    return event_class.from_dict(data)


def serialize_event(event: ProgressEvent) -> Dict[str, Any]:
    """Serialize event to dictionary."""
    return event.to_dict()


# Common progress data structures
@dataclass
class ProgressSummary:
    """Summary of progress for a task or node."""
    correlation_id: str
    name: str
    status: ProgressStatus
    progress_percentage: float
    start_time: datetime
    end_time: Optional[datetime] = field(default=None)
    duration: Optional[float] = field(default=None)
    error_count: int = field(default=0)
    last_operation: str = field(default="")
    sub_tasks: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "name": self.name,
            "status": self.status.value,
            "progress_percentage": self.progress_percentage,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "error_count": self.error_count,
            "last_operation": self.last_operation,
            "sub_tasks": self.sub_tasks
        }


@dataclass
class ProgressTimeline:
    """Timeline of progress events for a task."""
    correlation_id: str
    task_name: str
    events: List[ProgressEvent] = field(default_factory=list)
    
    def add_event(self, event: ProgressEvent) -> None:
        """Add an event to the timeline."""
        self.events.append(event)
    
    def get_events_by_type(self, event_type: ProgressEventType) -> List[ProgressEvent]:
        """Get events of a specific type."""
        return [event for event in self.events if event.event_type == event_type]
    
    def get_events_by_node(self, node_name: str) -> List[ProgressEvent]:
        """Get events for a specific node."""
        return [event for event in self.events if hasattr(event, 'node_name') and event.node_name == node_name]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "task_name": self.task_name,
            "events": [serialize_event(event) for event in self.events]
        }