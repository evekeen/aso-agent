"""Progress tracking service with in-memory storage for ASO analysis workflows."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .correlation_id import get_or_create_correlation_id, format_correlation_id


class ProgressEventType(Enum):
    """Types of progress events."""
    START = "start"
    UPDATE = "update"  
    ERROR = "error"
    COMPLETION = "completion"
    SUB_TASK_START = "sub_task_start"
    SUB_TASK_UPDATE = "sub_task_update"
    SUB_TASK_COMPLETION = "sub_task_completion"


@dataclass
class ProgressEvent:
    """Individual progress event."""
    correlation_id: str
    event_type: ProgressEventType
    timestamp: datetime
    node_name: str
    current_operation: str
    progress_percentage: float = 0.0
    elapsed_time: float = 0.0
    status: str = "running"
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: int = 0
    recovery_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgress:
    """Progress tracking for a complete task."""
    correlation_id: str
    task_name: str
    start_time: datetime
    current_node: str = ""
    current_operation: str = ""
    overall_progress: float = 0.0
    elapsed_time: float = 0.0
    status: str = "running"
    events: List[ProgressEvent] = field(default_factory=list)
    sub_tasks: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class ProgressTracker:
    """In-memory progress tracking service."""
    
    def __init__(self, cleanup_ttl_seconds: int = 3600):
        self._tasks: Dict[str, TaskProgress] = {}
        self._cleanup_ttl = cleanup_ttl_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
    async def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_loop(self):
        """Background task to clean up expired progress data."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_expired_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Progress cleanup error: {e}")
    
    async def _cleanup_expired_tasks(self):
        """Remove expired tasks from memory."""
        async with self._lock:
            now = datetime.now()
            expired_ids = []
            
            for correlation_id, task in self._tasks.items():
                if task.status in ["completed", "failed"]:
                    time_since_completion = (now - task.last_update).total_seconds()
                    if time_since_completion > self._cleanup_ttl:
                        expired_ids.append(correlation_id)
            
            for correlation_id in expired_ids:
                del self._tasks[correlation_id]
                print(f"Cleaned up expired task: {correlation_id}")
    
    async def start_task(self, correlation_id: Optional[str] = None, task_name: str = "ASO Analysis") -> str:
        """Start tracking a new task. Returns the correlation ID."""
        if correlation_id is None:
            correlation_id = get_or_create_correlation_id()
            
        async with self._lock:
            task = TaskProgress(
                correlation_id=correlation_id,
                task_name=task_name,
                start_time=datetime.now()
            )
            self._tasks[correlation_id] = task
            
            # Add start event
            event = ProgressEvent(
                correlation_id=correlation_id,
                event_type=ProgressEventType.START,
                timestamp=datetime.now(),
                node_name="workflow",
                current_operation=f"Starting {task_name}",
                status="running"
            )
            task.events.append(event)
            
        await self.start_cleanup_task()
        return correlation_id
    
    async def update_progress(
        self,
        correlation_id: str,
        node_name: str,
        current_operation: str,
        progress_percentage: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update progress for a task."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            now = datetime.now()
            elapsed = (now - task.start_time).total_seconds()
            
            # Update task progress
            task.current_node = node_name
            task.current_operation = current_operation
            task.overall_progress = progress_percentage
            task.elapsed_time = elapsed
            task.last_update = now
            
            # Add progress event
            event = ProgressEvent(
                correlation_id=correlation_id,
                event_type=ProgressEventType.UPDATE,
                timestamp=now,
                node_name=node_name,
                current_operation=current_operation,
                progress_percentage=progress_percentage,
                elapsed_time=elapsed,
                metadata=metadata or {}
            )
            task.events.append(event)
    
    async def update_sub_task_progress(
        self,
        correlation_id: str,
        sub_task_name: str,
        progress_percentage: float,
        current_operation: str,
        node_name: str = "sub_task"
    ) -> None:
        """Update progress for a sub-task."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            # Update sub-task progress
            task.sub_tasks[sub_task_name] = progress_percentage
            
            # Add sub-task event
            event = ProgressEvent(
                correlation_id=correlation_id,
                event_type=ProgressEventType.SUB_TASK_UPDATE,
                timestamp=datetime.now(),
                node_name=node_name,
                current_operation=current_operation,
                progress_percentage=progress_percentage,
                elapsed_time=(datetime.now() - task.start_time).total_seconds(),
                metadata={"sub_task": sub_task_name}
            )
            task.events.append(event)
    
    async def report_error(
        self,
        correlation_id: str,
        node_name: str,
        error_message: str,
        error_type: str = "error",
        retry_count: int = 0,
        recovery_action: Optional[str] = None
    ) -> None:
        """Report an error during task execution."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            task.error_count += 1
            task.last_update = datetime.now()
            
            # Add error event
            event = ProgressEvent(
                correlation_id=correlation_id,
                event_type=ProgressEventType.ERROR,
                timestamp=datetime.now(),
                node_name=node_name,
                current_operation=f"Error in {node_name}",
                elapsed_time=(datetime.now() - task.start_time).total_seconds(),
                status="error",
                error_message=error_message,
                error_type=error_type,
                retry_count=retry_count,
                recovery_action=recovery_action
            )
            task.events.append(event)
    
    async def complete_task(
        self,
        correlation_id: str,
        success: bool = True,
        final_message: str = "Task completed"
    ) -> None:
        """Mark a task as completed."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            task.status = "completed" if success else "failed"
            task.overall_progress = 100.0 if success else task.overall_progress
            task.last_update = datetime.now()
            
            # Add completion event
            event = ProgressEvent(
                correlation_id=correlation_id,
                event_type=ProgressEventType.COMPLETION,
                timestamp=datetime.now(),
                node_name="workflow",
                current_operation=final_message,
                progress_percentage=task.overall_progress,
                elapsed_time=(datetime.now() - task.start_time).total_seconds(),
                status=task.status
            )
            task.events.append(event)
    
    async def get_task_progress(self, correlation_id: str) -> Optional[TaskProgress]:
        """Get current progress for a task."""
        async with self._lock:
            return self._tasks.get(correlation_id)
    
    async def get_all_tasks(self) -> Dict[str, TaskProgress]:
        """Get all current tasks."""
        async with self._lock:
            return self._tasks.copy()
    
    async def get_task_events(self, correlation_id: str) -> List[ProgressEvent]:
        """Get all events for a task."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            return task.events.copy() if task else []
    
    async def cleanup_task(self, correlation_id: str) -> bool:
        """Manually clean up a specific task."""
        async with self._lock:
            if correlation_id in self._tasks:
                del self._tasks[correlation_id]
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the progress tracker."""
        return {
            "total_tasks": len(self._tasks),
            "active_tasks": len([t for t in self._tasks.values() if t.status == "running"]),
            "completed_tasks": len([t for t in self._tasks.values() if t.status == "completed"]),
            "failed_tasks": len([t for t in self._tasks.values() if t.status == "failed"]),
            "cleanup_ttl_seconds": self._cleanup_ttl
        }
    
    def format_progress_log(self, correlation_id: str, message: str) -> str:
        """Format a progress log message with correlation ID."""
        return f"{format_correlation_id(correlation_id)} {message}"


# Global instance
_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker


async def shutdown_progress_tracker():
    """Shutdown the global progress tracker."""
    global _progress_tracker
    if _progress_tracker:
        await _progress_tracker.stop_cleanup_task()
        _progress_tracker = None