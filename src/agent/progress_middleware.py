"""Progress tracking middleware for LangGraph workflow nodes."""

import functools
import asyncio
from typing import Any, Dict, Callable, Optional, Union, List
from datetime import datetime
from dataclasses import dataclass

from lib.progress_tracker import get_progress_tracker
from lib.correlation_id import get_correlation_id, set_correlation_id


@dataclass
class NodeMetadata:
    """Metadata for a LangGraph node."""
    name: str
    description: str
    estimated_duration: Optional[float] = None
    sub_tasks: Optional[List[str]] = None


def with_progress_tracking(
    node_name: str,
    description: str = "",
    estimated_duration: Optional[float] = None,
    sub_tasks: Optional[List[str]] = None
):
    """
    Decorator to add progress tracking to LangGraph nodes.
    
    Args:
        node_name: Name of the node for progress tracking
        description: Description of what the node does
        estimated_duration: Estimated duration in seconds (optional)
        sub_tasks: List of sub-task names for detailed tracking (optional)
    
    Usage:
        @with_progress_tracking("collect_app_ideas", "Collecting app ideas for analysis")
        def collect_app_ideas(state: dict) -> dict:
            return {"ideas": ["golf shot tracer", "snoring tracker"]}
    """
    def decorator(func: Callable) -> Callable:
        metadata = NodeMetadata(
            name=node_name,
            description=description,
            estimated_duration=estimated_duration,
            sub_tasks=sub_tasks or []
        )
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(state: dict, config: Optional[dict] = None) -> dict:
                return await _execute_with_progress(func, state, config, metadata)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(state: dict, config: Optional[dict] = None) -> dict:
                # For sync functions, we need to handle the async context properly
                try:
                    # Check if we're in an async context
                    loop = asyncio.get_running_loop()
                    # If we are, we need to create a new event loop in a thread
                    import concurrent.futures
                    import threading
                    
                    def run_in_thread():
                        return asyncio.run(_execute_with_progress(func, state, config, metadata))
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        return future.result()
                        
                except RuntimeError:
                    # No event loop running, we can use asyncio.run directly
                    return asyncio.run(_execute_with_progress(func, state, config, metadata))
            return sync_wrapper
    
    return decorator


async def _execute_with_progress(
    func: Callable,
    state: dict,
    config: Optional[dict],
    metadata: NodeMetadata
) -> dict:
    """Execute a node function with progress tracking."""
    tracker = get_progress_tracker()
    
    # Get or create correlation ID
    correlation_id = get_correlation_id()
    if not correlation_id:
        # Try to get from state first
        correlation_id = state.get("correlation_id")
        if correlation_id:
            set_correlation_id(correlation_id)
        else:
            # Create new correlation ID and start task
            correlation_id = await tracker.start_task(
                task_name="ASO Analysis",
                workflow_steps=_get_workflow_steps()
            )
            set_correlation_id(correlation_id)
    
    # Start node execution
    await tracker.start_node(
        correlation_id=correlation_id,
        node_name=metadata.name,
        current_operation=metadata.description or f"Executing {metadata.name}"
    )
    
    try:
        # Execute the actual node function
        if asyncio.iscoroutinefunction(func):
            result = await func(state, config) if config else await func(state)
        else:
            result = func(state, config) if config else func(state)
        
        # Complete node successfully
        await tracker.complete_node(
            correlation_id=correlation_id,
            node_name=metadata.name,
            success=True
        )
        
        # Add correlation_id to result state if not present
        if isinstance(result, dict) and "correlation_id" not in result:
            result["correlation_id"] = correlation_id
        
        return result
        
    except Exception as e:
        # Report error
        await tracker.report_error(
            correlation_id=correlation_id,
            node_name=metadata.name,
            error_message=str(e),
            error_type=type(e).__name__,
            stack_trace=str(e)
        )
        
        # Complete node with failure
        await tracker.complete_node(
            correlation_id=correlation_id,
            node_name=metadata.name,
            success=False
        )
        
        # Re-raise the exception
        raise


def _get_workflow_steps() -> List[str]:
    """Get the standard workflow steps for ASO analysis."""
    return [
        "collect_app_ideas",
        "generate_initial_keywords",
        "search_apps_for_keywords",
        "get_keyword_total_market_size",
        "filter_keywords_by_market_size",
        "analyze_keyword_difficulty",
        "generate_final_report"
    ]


def update_sub_task_progress(
    sub_task_name: str,
    progress_percentage: float,
    current_operation: str,
    node_name: Optional[str] = None
):
    """
    Update progress for a sub-task within a node.
    
    Args:
        sub_task_name: Name of the sub-task
        progress_percentage: Progress percentage (0-100)
        current_operation: Description of current operation
        node_name: Name of the parent node (auto-detected if not provided)
    """
    async def _update():
        tracker = get_progress_tracker()
        correlation_id = get_correlation_id()
        
        if correlation_id:
            await tracker.update_sub_task_progress(
                correlation_id=correlation_id,
                sub_task_name=sub_task_name,
                progress_percentage=progress_percentage,
                current_operation=current_operation,
                node_name=node_name or "current_node"
            )
    
    # Run the update asynchronously
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_update())
    except RuntimeError:
        # If no event loop is running, run synchronously
        asyncio.run(_update())


def update_node_progress(
    progress_percentage: float,
    current_operation: str,
    node_name: Optional[str] = None
):
    """
    Update progress for the current node.
    
    Args:
        progress_percentage: Progress percentage (0-100)
        current_operation: Description of current operation
        node_name: Name of the node (auto-detected if not provided)
    """
    async def _update():
        tracker = get_progress_tracker()
        correlation_id = get_correlation_id()
        
        if correlation_id:
            await tracker.update_progress(
                correlation_id=correlation_id,
                node_name=node_name or "current_node",
                current_operation=current_operation,
                progress_percentage=progress_percentage
            )
    
    # Run the update asynchronously
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_update())
    except RuntimeError:
        # If no event loop is running, run synchronously
        asyncio.run(_update())


class ProgressContext:
    """Context manager for tracking progress within a node."""
    
    def __init__(self, node_name: str, total_items: int):
        self.node_name = node_name
        self.total_items = total_items
        self.current_item = 0
        self.correlation_id = None
        self.tracker = None
    
    async def __aenter__(self):
        self.tracker = get_progress_tracker()
        self.correlation_id = get_correlation_id()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def update(self, current_item: int, operation: str):
        """Update progress based on current item count."""
        self.current_item = current_item
        progress = (current_item / self.total_items) * 100 if self.total_items > 0 else 0
        
        if self.correlation_id and self.tracker:
            await self.tracker.update_progress(
                correlation_id=self.correlation_id,
                node_name=self.node_name,
                current_operation=operation,
                progress_percentage=progress
            )
    
    async def increment(self, operation: str):
        """Increment progress by 1 item."""
        await self.update(self.current_item + 1, operation)