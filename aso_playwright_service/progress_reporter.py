"""Progress reporting for Playwright microservice."""

import asyncio
import aiohttp
import functools
from typing import Optional, Dict, Any, Callable
import os
from dataclasses import dataclass
from datetime import datetime


class ProgressReporter:
    """Simple progress reporter for Playwright microservice."""
    
    def __init__(self, correlation_id: str, main_service_url: str = None):
        """
        Initialize progress reporter.
        
        Args:
            correlation_id: Correlation ID for tracking across services
            main_service_url: URL of the main service progress endpoint
        """
        self.correlation_id = correlation_id
        self.main_service_url = main_service_url or os.getenv('MAIN_SERVICE_URL', 'http://localhost:8080')
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _send_progress_update(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Send progress update to main service.
        
        Args:
            event_type: Type of progress event
            data: Event data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.session:
            return False
            
        try:
            progress_data = {
                "correlation_id": self.correlation_id,
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "service_name": "playwright_microservice",
                **data
            }
            
            endpoint = f"{self.main_service_url}/progress/update"
            
            async with self.session.post(
                endpoint,
                json=progress_data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
                    
        except Exception as e:
            print(f"⚠️ Failed to send progress update: {e}")
            return False
    
    async def report_step(self, step_name: str, description: str, progress_percentage: float = 0.0) -> None:
        """Report a workflow step."""
        await self._send_progress_update("step_progress", {
            "step_name": step_name,
            "description": description,
            "progress_percentage": progress_percentage,
            "current_operation": description
        })
    
    async def report_error(self, error_message: str, error_type: str = "RuntimeError", 
                          step_name: str = "unknown", retry_attempt: int = 0) -> None:
        """Report an error during processing."""
        await self._send_progress_update("error", {
            "error_message": error_message,
            "error_type": error_type,
            "step_name": step_name,
            "retry_attempt": retry_attempt,
            "current_operation": f"Error in {step_name}: {error_message}"
        })
    
    async def report_keywords_processed(self, keywords: Dict[str, Any], total_count: int) -> None:
        """Report keyword processing results."""
        await self._send_progress_update("keywords_processed", {
            "keywords_processed": len(keywords),
            "total_keywords": total_count,
            "progress_percentage": (len(keywords) / total_count) * 100 if total_count > 0 else 0,
            "current_operation": f"Processed {len(keywords)}/{total_count} keywords"
        })


def with_progress_tracking(step_name: str, description: str):
    """
    Decorator to add progress tracking to business logic methods.
    
    Args:
        step_name: Name of the step for progress tracking
        description: Description of what the step does
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Only report progress if progress reporter is available
            if hasattr(self, 'progress_reporter') and self.progress_reporter:
                await self.progress_reporter.report_step(step_name, description)
            
            try:
                result = await func(self, *args, **kwargs)
                
                # Report completion
                if hasattr(self, 'progress_reporter') and self.progress_reporter:
                    await self.progress_reporter.report_step(step_name, f"Completed {description}", 100.0)
                
                return result
                
            except Exception as e:
                # Report error
                if hasattr(self, 'progress_reporter') and self.progress_reporter:
                    await self.progress_reporter.report_error(
                        error_message=str(e),
                        error_type=type(e).__name__,
                        step_name=step_name
                    )
                raise
                
        return wrapper
    return decorator


def get_progress_reporter(correlation_id: str) -> ProgressReporter:
    """
    Get a progress reporter instance.
    
    Args:
        correlation_id: Correlation ID for tracking
        
    Returns:
        ProgressReporter instance
    """
    return ProgressReporter(correlation_id) if correlation_id else None