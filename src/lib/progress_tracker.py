"""Progress tracking service with in-memory storage for ASO analysis workflows."""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from .correlation_id import get_or_create_correlation_id, format_correlation_id
from .progress_models import (
    ProgressEvent,
    ProgressStatus,
    WorkflowStartEvent,
    WorkflowCompletionEvent,
    NodeStartEvent,
    NodeUpdateEvent,
    NodeCompletionEvent,
    SubTaskUpdateEvent,
    ErrorEvent,
    MicroserviceUpdateEvent,
    ProgressTimeline,
    serialize_event
)


@dataclass
class NodeProgress:
    """Progress tracking for a single node."""
    node_name: str
    progress_percentage: float = 0.0
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_operation: str = ""
    sub_tasks: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0


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
    status: ProgressStatus = ProgressStatus.RUNNING
    events: List[ProgressEvent] = field(default_factory=list)
    sub_tasks: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    node_progress: Dict[str, NodeProgress] = field(default_factory=dict)
    workflow_steps: List[str] = field(default_factory=list)
    timeline: Optional[ProgressTimeline] = field(default=None)


class ProgressTracker:
    """In-memory progress tracking service."""
    
    def __init__(self, cleanup_ttl_seconds: int = 3600):
        self._tasks: Dict[str, TaskProgress] = {}
        self._cleanup_ttl = cleanup_ttl_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    def _add_event(self, task: TaskProgress, event: ProgressEvent) -> None:
        """Add an event to both task events and timeline."""
        task.events.append(event)
        if task.timeline:
            task.timeline.add_event(event)
        
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
                if task.status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED]:
                    time_since_completion = (now - task.last_update).total_seconds()
                    if time_since_completion > self._cleanup_ttl:
                        expired_ids.append(correlation_id)
            
            for correlation_id in expired_ids:
                del self._tasks[correlation_id]
                print(f"Cleaned up expired task: {correlation_id}")
    
    async def start_task(
        self, 
        correlation_id: Optional[str] = None, 
        task_name: str = "ASO Analysis",
        workflow_steps: Optional[List[str]] = None
    ) -> str:
        """Start tracking a new task. Returns the correlation ID."""
        if correlation_id is None:
            correlation_id = get_or_create_correlation_id()
            
        if workflow_steps is None:
            workflow_steps = [
                "collect_app_ideas",
                "generate_initial_keywords", 
                "search_apps_for_keywords",
                "get_keyword_total_market_size",
                "filter_keywords_by_market_size",
                "analyze_keyword_difficulty",
                "generate_final_report"
            ]
            
        async with self._lock:
            now = datetime.now()
            
            # Create timeline
            timeline = ProgressTimeline(
                correlation_id=correlation_id,
                task_name=task_name
            )
            
            task = TaskProgress(
                correlation_id=correlation_id,
                task_name=task_name,
                start_time=now,
                workflow_steps=workflow_steps,
                timeline=timeline
            )
            self._tasks[correlation_id] = task
            
            # Initialize node progress for all workflow steps
            for step in workflow_steps:
                task.node_progress[step] = NodeProgress(node_name=step)
            
            # Add start event using new event model
            event = WorkflowStartEvent(
                correlation_id=correlation_id,
                timestamp=now,
                task_name=task_name,
                workflow_steps=workflow_steps
            )
            self._add_event(task, event)
            
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
            
            # Add progress event using new event model
            event = NodeUpdateEvent(
                correlation_id=correlation_id,
                timestamp=now,
                node_name=node_name,
                current_operation=current_operation,
                progress_percentage=progress_percentage,
                status=ProgressStatus.RUNNING,
                elapsed_time=elapsed,
                metadata=metadata or {}
            )
            self._add_event(task, event)
    
    async def update_sub_task_progress(
        self,
        correlation_id: str,
        sub_task_name: str,
        progress_percentage: float,
        current_operation: str,
        node_name: str = "default_node"
    ) -> None:
        """Update progress for a sub-task."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            # Update sub-task progress
            task.sub_tasks[sub_task_name] = progress_percentage
            
            # Add sub-task event using new event model
            now = datetime.now()
            event = SubTaskUpdateEvent(
                correlation_id=correlation_id,
                timestamp=now,
                node_name=node_name,
                sub_task_name=sub_task_name,
                current_operation=current_operation,
                progress_percentage=progress_percentage,
                status=ProgressStatus.RUNNING,
                elapsed_time=(now - task.start_time).total_seconds(),
                metadata={"sub_task": sub_task_name}
            )
            self._add_event(task, event)
    
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
            "active_tasks": len([t for t in self._tasks.values() if t.status == ProgressStatus.RUNNING]),
            "completed_tasks": len([t for t in self._tasks.values() if t.status == ProgressStatus.COMPLETED]),
            "failed_tasks": len([t for t in self._tasks.values() if t.status == ProgressStatus.FAILED]),
            "cleanup_ttl_seconds": self._cleanup_ttl
        }
    
    def format_progress_log(self, correlation_id: str, message: str) -> str:
        """Format a progress log message with correlation ID."""
        return f"{format_correlation_id(correlation_id)} {message}"
    
    async def report_error(
        self,
        correlation_id: str,
        node_name: str,
        error_message: str,
        error_type: str = "error",
        retry_count: int = 0,
        recovery_action: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> None:
        """Report an error during task execution using structured event model."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            now = datetime.now()
            task.error_count += 1
            task.last_update = now
            
            # Add error event using new event model
            event = ErrorEvent(
                correlation_id=correlation_id,
                timestamp=now,
                node_name=node_name,
                error_type=error_type,
                error_message=error_message,
                retry_count=retry_count,
                recovery_action=recovery_action,
                stack_trace=stack_trace,
                elapsed_time=(now - task.start_time).total_seconds()
            )
            self._add_event(task, event)
    
    async def complete_task(
        self,
        correlation_id: str,
        success: bool = True,
        final_message: str = "Task completed",
        summary: Optional[str] = None
    ) -> None:
        """Mark a task as completed using structured event model."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            now = datetime.now()
            task.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
            task.overall_progress = 100.0 if success else task.overall_progress
            task.last_update = now
            
            # Calculate total duration
            total_duration = (now - task.start_time).total_seconds()
            
            # Add completion event using new event model
            event = WorkflowCompletionEvent(
                correlation_id=correlation_id,
                timestamp=now,
                task_name=task.task_name,
                status=task.status,
                final_progress=task.overall_progress,
                total_duration=total_duration,
                elapsed_time=total_duration,
                error_count=task.error_count,
                summary=summary or final_message
            )
            self._add_event(task, event)
    
    async def get_serialized_events(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get serialized events for a task."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return []
            
            return [serialize_event(event) for event in task.events]
    
    async def start_node(
        self,
        correlation_id: str,
        node_name: str,
        current_operation: str = ""
    ) -> None:
        """Start tracking a specific node."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            now = datetime.now()
            
            # Update node progress
            if node_name in task.node_progress:
                node_progress = task.node_progress[node_name]
                node_progress.status = ProgressStatus.RUNNING
                node_progress.start_time = now
                node_progress.current_operation = current_operation
                node_progress.progress_percentage = 0.0
            
            # Update overall task progress
            task.current_node = node_name
            task.current_operation = current_operation
            task.last_update = now
            
            # Add event using new event model
            event = NodeStartEvent(
                correlation_id=correlation_id,
                timestamp=now,
                node_name=node_name,
                current_operation=current_operation,
                elapsed_time=(now - task.start_time).total_seconds()
            )
            self._add_event(task, event)
            
            # Recalculate overall progress
            await self._update_overall_progress(correlation_id)
    
    async def complete_node(
        self,
        correlation_id: str,
        node_name: str,
        success: bool = True
    ) -> None:
        """Complete a specific node."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            now = datetime.now()
            
            # Update node progress
            if node_name in task.node_progress:
                node_progress = task.node_progress[node_name]
                node_progress.status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
                node_progress.end_time = now
                node_progress.progress_percentage = 100.0 if success else node_progress.progress_percentage
                
                if not success:
                    node_progress.error_count += 1
                    task.error_count += 1
            
            task.last_update = now
            
            # Calculate duration
            duration = 0.0
            if node_name in task.node_progress and task.node_progress[node_name].start_time:
                duration = (now - task.node_progress[node_name].start_time).total_seconds()
            
            # Add event using new event model
            event = NodeCompletionEvent(
                correlation_id=correlation_id,
                timestamp=now,
                node_name=node_name,
                status=ProgressStatus.COMPLETED if success else ProgressStatus.FAILED,
                final_progress=100.0 if success else task.node_progress[node_name].progress_percentage,
                duration=duration,
                elapsed_time=(now - task.start_time).total_seconds()
            )
            self._add_event(task, event)
            
            # Recalculate overall progress
            await self._update_overall_progress(correlation_id)
    
    async def update_node_progress(
        self,
        correlation_id: str,
        node_name: str,
        progress_percentage: float,
        current_operation: str = "",
        sub_task_name: Optional[str] = None,
        sub_task_progress: Optional[float] = None
    ) -> None:
        """Update progress for a specific node."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            now = datetime.now()
            
            # Update node progress
            if node_name in task.node_progress:
                node_progress = task.node_progress[node_name]
                node_progress.progress_percentage = progress_percentage
                node_progress.current_operation = current_operation
                
                # Update sub-task progress if provided
                if sub_task_name and sub_task_progress is not None:
                    node_progress.sub_tasks[sub_task_name] = sub_task_progress
            
            # Update overall task progress
            task.current_node = node_name
            task.current_operation = current_operation
            task.last_update = now
            
            # Add event using new event model
            if sub_task_name:
                event = SubTaskUpdateEvent(
                    correlation_id=correlation_id,
                    timestamp=now,
                    node_name=node_name,
                    sub_task_name=sub_task_name,
                    current_operation=current_operation,
                    progress_percentage=sub_task_progress if sub_task_progress else progress_percentage,
                    status=ProgressStatus.RUNNING,
                    elapsed_time=(now - task.start_time).total_seconds()
                )
            else:
                event = NodeUpdateEvent(
                    correlation_id=correlation_id,
                    timestamp=now,
                    node_name=node_name,
                    current_operation=current_operation,
                    progress_percentage=progress_percentage,
                    status=ProgressStatus.RUNNING,
                    elapsed_time=(now - task.start_time).total_seconds()
                )
            self._add_event(task, event)
            
            # Recalculate overall progress
            await self._update_overall_progress(correlation_id)
    
    async def _update_overall_progress(self, correlation_id: str) -> None:
        """Recalculate overall progress based on node progress."""
        task = self._tasks.get(correlation_id)
        if not task:
            return
        
        if not task.workflow_steps:
            return
        
        # Calculate weighted average progress
        total_progress = 0.0
        completed_nodes = 0
        
        for step in task.workflow_steps:
            if step in task.node_progress:
                node_progress = task.node_progress[step]
                total_progress += node_progress.progress_percentage
                if node_progress.status == ProgressStatus.COMPLETED:
                    completed_nodes += 1
        
        # Calculate overall progress as percentage
        if task.workflow_steps:
            task.overall_progress = total_progress / len(task.workflow_steps)
        
        # Update status based on progress
        if completed_nodes == len(task.workflow_steps):
            task.status = ProgressStatus.COMPLETED
        elif any(node.status == ProgressStatus.FAILED for node in task.node_progress.values()):
            task.status = ProgressStatus.FAILED
        else:
            task.status = ProgressStatus.RUNNING
    
    async def aggregate_microservice_progress(
        self,
        correlation_id: str,
        service_name: str,
        service_progress: Dict[str, Any]
    ) -> None:
        """Aggregate progress updates from microservices."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return
            
            now = datetime.now()
            
            # Map service progress to node progress
            # This assumes the service reports progress in a standard format
            node_name = service_progress.get("node_name", service_name)
            progress_percentage = service_progress.get("progress_percentage", 0.0)
            current_operation = service_progress.get("current_operation", f"Processing in {service_name}")
            sub_tasks = service_progress.get("sub_tasks", {})
            
            # Update node progress
            if node_name in task.node_progress:
                node_progress = task.node_progress[node_name]
                node_progress.progress_percentage = progress_percentage
                node_progress.current_operation = current_operation
                node_progress.sub_tasks.update(sub_tasks)
                
                # Update status based on progress
                if progress_percentage >= 100.0:
                    node_progress.status = ProgressStatus.COMPLETED
                    node_progress.end_time = now
                elif progress_percentage > 0:
                    node_progress.status = ProgressStatus.RUNNING
                    if not node_progress.start_time:
                        node_progress.start_time = now
            
            # Update overall task
            task.current_node = node_name
            task.current_operation = current_operation
            task.last_update = now
            
            # Add event using new event model
            event = MicroserviceUpdateEvent(
                correlation_id=correlation_id,
                timestamp=now,
                service_name=service_name,
                node_name=node_name,
                current_operation=current_operation,
                progress_percentage=progress_percentage,
                status=ProgressStatus.COMPLETED if progress_percentage >= 100.0 else ProgressStatus.RUNNING,
                elapsed_time=(now - task.start_time).total_seconds(),
                sub_tasks=sub_tasks
            )
            self._add_event(task, event)
            
            # Recalculate overall progress
            await self._update_overall_progress(correlation_id)
    
    async def get_aggregated_progress(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get aggregated progress view for a task."""
        async with self._lock:
            task = self._tasks.get(correlation_id)
            if not task:
                return None
            
            # Build aggregated progress view
            workflow_progress = []
            for step in task.workflow_steps:
                if step in task.node_progress:
                    node = task.node_progress[step]
                    workflow_progress.append({
                        "node_name": step,
                        "status": node.status.value,
                        "progress_percentage": node.progress_percentage,
                        "current_operation": node.current_operation,
                        "sub_tasks": node.sub_tasks,
                        "start_time": node.start_time.isoformat() if node.start_time else None,
                        "end_time": node.end_time.isoformat() if node.end_time else None,
                        "error_count": node.error_count
                    })
            
            return {
                "correlation_id": correlation_id,
                "task_name": task.task_name,
                "overall_progress": task.overall_progress,
                "status": task.status.value,
                "current_node": task.current_node,
                "current_operation": task.current_operation,
                "elapsed_time": task.elapsed_time,
                "start_time": task.start_time.isoformat(),
                "last_update": task.last_update.isoformat(),
                "error_count": task.error_count,
                "workflow_progress": workflow_progress,
                "event_count": len(task.events),
                "timeline": task.timeline.to_dict() if task.timeline else None
            }


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