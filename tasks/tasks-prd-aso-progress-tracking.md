# Implementation Tasks: ASO Analysis Progress Tracking

## Relevant Files

- `src/lib/progress_tracker.py` - Core progress tracking service with in-memory storage and event management
- `src/lib/progress_tracker.py` - Core progress tracking service with in-memory storage, event management, and cleanup
- `src/lib/correlation_id.py` - Correlation ID utilities for tracking requests across distributed services
- `tests/test_correlation_id.py` - Unit tests for correlation ID utilities (14 test cases)
- `tests/test_progress_tracker.py` - Unit tests for progress tracker (16 test cases)
- `src/agent/progress_middleware.py` - LangGraph middleware to emit progress events from workflow nodes
- `src/agent/progress_middleware.test.py` - Unit tests for progress middleware
- `aso_playwright_service/progress_reporter.py` - Progress reporting integration for Playwright service
- `aso_playwright_service/progress_reporter.test.py` - Unit tests for progress reporter
- `src/api/progress_routes.py` - FastAPI routes for progress polling endpoints
- `src/api/progress_routes.test.py` - Unit tests for progress API routes
- `src/lib/correlation_id.py` - Utility for generating and managing correlation IDs across services
- `src/lib/correlation_id.test.py` - Unit tests for correlation ID utilities

### Notes

- Unit tests should be placed alongside the code files they are testing
- Use `pytest` to run tests: `pytest src/lib/progress_tracker.test.py`
- The progress tracking system should be implemented as a separate concern from business logic
- Progress data will be stored in memory only and cleaned up after task completion

## Tasks

- [ ] 1.0 Implement Core Progress Tracking Infrastructure
  - [x] 1.1 Create progress tracker service with in-memory storage (`src/lib/progress_tracker.py`)
  - [x] 1.2 Implement event-based progress event system with timestamps and correlation IDs
  - [ ] 1.3 Add progress aggregation logic to combine LangGraph and microservice updates
  - [ ] 1.4 Create progress data models for different event types (start, update, error, completion)
  - [ ] 1.5 Implement memory cleanup and TTL for progress data
  - [ ] 1.6 Add unit tests for progress tracker core functionality

- [ ] 2.0 Integrate Progress Tracking with LangGraph Workflow
  - [ ] 2.1 Create LangGraph middleware to intercept node execution (`src/agent/progress_middleware.py`)
  - [ ] 2.2 Add progress event emission at key workflow milestones (node start, completion, error)
  - [ ] 2.3 Implement sub-progress tracking for long-running operations (keyword processing loops)
  - [ ] 2.4 Add correlation ID generation and propagation through workflow state
  - [ ] 2.5 Update existing nodes to emit meaningful progress descriptions and percentages
  - [ ] 2.6 Add unit tests for progress middleware integration

- [ ] 3.0 Add Progress Reporting to Playwright Microservice
  - [ ] 3.1 Create progress reporter for Playwright service (`aso_playwright_service/progress_reporter.py`)
  - [ ] 3.2 Integrate progress reporting into existing workflow steps (login, keyword processing, extraction)
  - [ ] 3.3 Add detailed sub-task progress for keyword-by-keyword processing
  - [ ] 3.4 Implement error reporting with retry attempt tracking
  - [ ] 3.5 Add correlation ID support to link service progress with main workflow
  - [ ] 3.6 Add unit tests for progress reporter functionality

- [ ] 4.0 Create Progress API Endpoints
  - [ ] 4.1 Implement FastAPI routes for progress polling (`src/api/progress_routes.py`)
  - [ ] 4.2 Add endpoint for retrieving current progress by correlation ID
  - [ ] 4.3 Create endpoint for progress history/timeline view
  - [ ] 4.4 Implement proper error handling and 404 responses for unknown tasks
  - [ ] 4.5 Add structured JSON responses following OpenAI-style progress format
  - [ ] 4.6 Add unit tests for progress API endpoints

- [ ] 5.0 Implement Progress Data Management and Cleanup
  - [ ] 5.1 Create correlation ID utility for generating unique task identifiers (`src/lib/correlation_id.py`)
  - [ ] 5.2 Implement automatic cleanup of completed task progress data
  - [ ] 5.3 Add progress data persistence during task execution with memory limits
  - [ ] 5.4 Create progress data export functionality for debugging and analysis
  - [ ] 5.5 Add monitoring and logging for progress system performance
  - [ ] 5.6 Add unit tests for data management and cleanup functionality