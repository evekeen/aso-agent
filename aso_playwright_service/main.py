"""ASO Playwright Microservice with task queue."""

import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import (
    AnalyzeKeywordsRequest,
    AnalyzeKeywordsResponse,
    HealthResponse,
    KeywordMetrics
)
from playwright_task import execute_keyword_analysis
from progress_reporter import get_progress_reporter


class TaskQueue:
    """Simple task queue with single worker."""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.worker_running = False
        self.current_task = None
    
    async def add_task(self, keywords: list, correlation_id: str = None) -> dict:
        """Add a task to the queue and wait for completion."""
        task_id = f"task_{int(time.time() * 1000)}"
        future = asyncio.Future()
        
        await self.queue.put({
            'id': task_id,
            'keywords': keywords,
            'correlation_id': correlation_id,
            'future': future
        })
        
        print(f"📋 Task {task_id} added to queue (queue size: {self.queue.qsize()})")
        
        # Wait for task completion
        return await future
    
    async def worker(self):
        """Background worker that processes tasks sequentially."""
        print("🚀 Task worker started")
        self.worker_running = True
        
        while self.worker_running:
            try:
                # Get next task
                task = await self.queue.get()
                self.current_task = task
                
                task_id = task['id']
                keywords = task['keywords']
                correlation_id = task.get('correlation_id')
                future = task['future']
                
                print(f"⚙️ Processing task {task_id} with {len(keywords)} keywords...")
                start_time = time.time()
                
                try:
                    # Execute the task with progress reporting
                    result = await execute_keyword_analysis(keywords, correlation_id)
                    
                    processing_time = time.time() - start_time
                    
                    # Convert to response format
                    metrics = {
                        keyword: KeywordMetrics(
                            difficulty=data.difficulty,
                            traffic=data.traffic
                        )
                        for keyword, data in result.items()
                    }
                    
                    response = {
                        'metrics': metrics,
                        'status': 'success',
                        'processing_time': processing_time,
                        'total_keywords': len(keywords)
                    }
                    
                    print(f"✅ Task {task_id} completed in {processing_time:.2f}s")
                    future.set_result(response)
                    
                except Exception as e:
                    print(f"❌ Task {task_id} failed: {e}")
                    error_response = {
                        'metrics': {},
                        'status': 'error',
                        'processing_time': time.time() - start_time,
                        'total_keywords': len(keywords),
                        'error': str(e)
                    }
                    future.set_result(error_response)
                
                finally:
                    self.current_task = None
                    self.queue.task_done()
                    
            except Exception as e:
                print(f"❌ Worker error: {e}")
                if self.current_task:
                    self.current_task['future'].set_exception(e)
                    self.current_task = None
    
    def stop(self):
        """Stop the worker."""
        self.worker_running = False
        print("🛑 Task worker stopped")
    
    def get_status(self):
        """Get queue status."""
        return {
            'queue_size': self.queue.qsize(),
            'worker_running': self.worker_running,
            'current_task': self.current_task['id'] if self.current_task else None
        }


# Global task queue
task_queue = TaskQueue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Start the background worker
    worker_task = asyncio.create_task(task_queue.worker())
    
    try:
        yield
    finally:
        # Stop the worker
        task_queue.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


# Create FastAPI app
app = FastAPI(
    title="ASO Playwright Service",
    description="Microservice for ASO Mobile keyword analysis using Playwright",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    status = task_queue.get_status()
    
    return HealthResponse(
        status="healthy",
        queue_size=status['queue_size'],
        service_healthy=status['worker_running']
    )


@app.get("/status")
async def get_status():
    """Get detailed service status."""
    return task_queue.get_status()


@app.post("/analyze-keywords", response_model=AnalyzeKeywordsResponse)
async def analyze_keywords(request: AnalyzeKeywordsRequest):
    """Analyze keywords using ASO Mobile automation."""
    
    if not request.keywords:
        raise HTTPException(status_code=400, detail="Keywords list cannot be empty")
    
    if len(request.keywords) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 keywords allowed per request")
    
    try:
        print(f"📨 Received request for {len(request.keywords)} keywords")
        
        # Add task to queue and wait for completion
        correlation_id = request.correlation_id
        result = await task_queue.add_task(request.keywords, correlation_id)
        
        if result.get('status') == 'error':
            raise HTTPException(
                status_code=500,
                detail=f"Task execution failed: {result.get('error', 'Unknown error')}"
            )
        
        return AnalyzeKeywordsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Request handling error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    print("🚀 Starting ASO Playwright Service...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )