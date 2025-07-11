# ASO Agent Development Guide

## Environment Setup

### Install Dependencies
```bash
# Activate virtual environment
source .venv/bin/activate

# Install project with dependencies
pip install -e .
```

### Key Dependencies
- `langgraph>=0.2.6` - Main graph framework
- `aiosqlite>=0.20.0` - Async SQLite for caching
- `aiohttp>=3.9.0` - Async HTTP requests
- `pydantic>=2.0.0` - Data validation

## LangGraph Node Development

### Basic Node Structure
```python
async def my_node(state: dict) -> dict:
    """
    Node description for what it does.
    """
    # Get data from state
    input_data = state.get("input_key", [])
    
    # Process data
    result = await process_data(input_data)
    
    # Return state updates
    return {"output_key": result}
```

### Async Cache Usage
```python
from lib.cache_store import get_cache_store

async def my_node(state: dict) -> dict:
    cache = get_cache_store()
    
    # Check cache
    cached = await cache.get_keyword_difficulty(keyword)
    if cached:
        return {"result": cached}
    
    # Process and cache
    result = expensive_operation()
    await cache.set_keyword_difficulty(keyword, result)
    
    return {"result": result}
```

### Conditional Routing
```python
from langgraph.types import Command
from typing import Literal

def routing_node(state: dict) -> Command[Literal["node_a", "node_b"]]:
    """Route based on state conditions."""
    if state.get("value", 0) > 1000:
        return Command(
            update={"filtered": True},
            goto="node_a"
        )
    else:
        return Command(
            update={"filtered": False}, 
            goto="node_b"
        )
```

### Graph Definition
```python
from langgraph.graph import StateGraph

graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node("node_name", node_function)
    .add_edge("node_a", "node_b")  # Direct edge
    .add_edge("start", "node_a")   # From start
    .compile(name="Graph Name")
)
```

## State Management

### State Schema
```python
@dataclass
class State(MessagesState):
    ideas: list[str]
    keywords: dict[str, list[str]]
    results: dict[str, float]
```

## Important Patterns

### Always Use Async for Cache
- All cache operations are async: `await cache.method()`
- Make node functions async if they use cache
- Use `aiosqlite` for non-blocking database operations

### Error Handling
```python
async def safe_node(state: dict) -> dict:
    try:
        result = await risky_operation()
        return {"success": result}
    except Exception as e:
        print(f"Error in node: {e}")
        return {"error": str(e)}
```

### Logging for Monitoring
```python
print(f"Processing {len(items)} items...")
print(f"✅ Completed successfully: {result}")
print(f"❌ Failed: {error}")
```