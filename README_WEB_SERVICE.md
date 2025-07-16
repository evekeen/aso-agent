# ASO Agent Web Service

A complete web service implementation for the ASO (App Store Optimization) analysis agent, providing both FastAPI backend and Streamlit frontend interfaces.

## Features

- **🚀 FastAPI Backend**: High-performance API with streaming support
- **📱 Streamlit Frontend**: Interactive chat interface with real-time progress tracking
- **📊 Rich Visualizations**: Market size charts, keyword difficulty analysis, opportunity matrices
- **⚡ Real-time Streaming**: Live progress updates during analysis
- **💾 Data Persistence**: SQLite-based conversation history and caching
- **🔒 Authentication**: Optional bearer token authentication
- **📈 Progress Tracking**: Visual progress bars and intermediate results

## Quick Start

### 1. Install Dependencies

```bash
# Install the project with dependencies
pip install -e .
```

### 2. Set up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# At minimum, set:
# - OPENAI_API_KEY
# - SENSOR_TOWER_API_KEY (optional)
# - ASO_MOBILE_API_KEY (optional)
```

### 3. Run the Service

**Option A: Run both services separately**

```bash
# Terminal 1: Start FastAPI backend
python src/run_service.py

# Terminal 2: Start Streamlit frontend  
python src/run_streamlit.py
```

**Option B: Using individual commands**

```bash
# Backend only
uvicorn src.service.service:app --host 0.0.0.0 --port 8080 --reload

# Frontend only
streamlit run src/streamlit_app.py --server.address=0.0.0.0 --server.port=8501
```

### 4. Access the Application

- **Streamlit Frontend**: http://localhost:8501
- **FastAPI Backend**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs

## Architecture

```
┌─────────────────┐    HTTP/SSE     ┌──────────────────┐
│   Streamlit UI  │ ◄──────────────► │   FastAPI        │
│   (Frontend)    │                 │   Service        │
│                 │                 │   (Backend)      │
│ • Chat Interface│                 │ • Agent Executor │
│ • Progress View │                 │ • SSE Streaming  │
│ • Results Viz   │                 │ • Authentication │
└─────────────────┘                 └──────────────────┘
                                             │
                                             ▼
                                   ┌──────────────────┐
                                   │   ASO LangGraph  │
                                   │   Agent          │
                                   │                  │
                                   │ • Keyword Gen    │
                                   │ • App Search     │
                                   │ • Market Analysis│
                                   │ • Difficulty Calc│
                                   └──────────────────┘
```

## API Endpoints

### Core Endpoints

- `GET /health` - Health check
- `GET /info` - Service metadata (agents, models)
- `POST /invoke` - Single request-response analysis
- `POST /stream` - Server-sent events streaming
- `POST /feedback` - Record user feedback
- `GET /history/{thread_id}` - Get conversation history

### Request Format

```json
{
  "message": "Analyze golf shot tracker and sleep monitoring app ideas",
  "model": "gpt-4o-mini",
  "thread_id": "optional-thread-id",
  "user_id": "optional-user-id",
  "agent_config": {
    "market_threshold": 50000,
    "keywords_per_idea": 20
  }
}
```

### Response Format

```json
{
  "type": "ai",
  "content": "ASO Analysis Complete! Golf Shot Tracker shows...",
  "custom_data": {
    "final_report": {
      "app_ideas": {
        "golf shot tracker": {
          "best_possible_market_size_usd": 125000,
          "keywords": {
            "golf tracker": {
              "difficulty_rating": 45.2,
              "traffic_rating": 78.5,
              "market_size_usd": 125000
            }
          }
        }
      }
    }
  }
}
```

## Frontend Features

### Chat Interface
- **Real-time chat** with the ASO agent
- **Progress tracking** during analysis phases
- **Intermediate results** display
- **Configuration panel** for analysis parameters

### Analysis Results
- **Overview tab**: Summary metrics and app idea comparison
- **Keywords tab**: Detailed keyword analysis with export options
- **Charts tab**: Interactive visualizations including:
  - Market size by app idea
  - Difficulty vs. traffic scatter plot
  - Opportunity matrix
  - Top keywords ranking

### Configuration Options
- **LLM Model selection**: Choose from available models
- **Market threshold**: Set minimum market size filter
- **Keywords per idea**: Control analysis depth
- **Streaming toggle**: Enable/disable real-time updates

## Configuration

### Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key  
DEFAULT_MODEL=gpt-4o-mini

# Service Configuration
HOST=0.0.0.0
PORT=8080
AUTH_SECRET=optional-api-secret

# Database
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=data/aso_agent.db

# ASO APIs
SENSOR_TOWER_API_KEY=your-sensor-tower-key
ASO_MOBILE_API_KEY=your-aso-mobile-key
ASO_EMAIL=your-aso-email
ASO_PASSWORD=your-aso-password

# Monitoring
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
```

### Analysis Parameters

- **Market Threshold**: Minimum market size (default: $50,000)
- **Keywords Per Idea**: Number of keywords to generate (default: 20)
- **Max Apps**: Maximum apps to analyze per keyword (default: 20)

## Development

### Project Structure

```
src/
├── service/
│   ├── service.py      # FastAPI server
│   └── settings.py     # Configuration
├── agents/
│   ├── agents.py       # Agent registry
│   └── aso_agent.py    # ASO agent wrapper
├── client/
│   └── client.py       # HTTP client
├── memory/
│   ├── __init__.py     # Memory initialization
│   └── sqlite.py       # SQLite persistence
├── schema/
│   └── schema.py       # Pydantic models
├── streamlit_app.py    # Frontend
├── run_service.py      # Backend startup
└── run_streamlit.py    # Frontend startup
```

### Adding New Features

1. **New Agent**: Add to `src/agents/agents.py`
2. **New Endpoint**: Add to `src/service/service.py`
3. **New Schema**: Add to `src/schema/schema.py`
4. **New Visualization**: Add to `src/streamlit_app.py`

### Testing

```bash
# Run basic functionality test
python -c "
from src.client.client import AgentClient
client = AgentClient()
print('Service available:', client.info is not None)
"

# Test streaming
curl -X POST http://localhost:8080/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Test analysis", "stream_tokens": true}'
```

## Deployment

### Docker (Future)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8080 8501
CMD ["python", "src/run_service.py"]
```

### Production Considerations

1. **Security**: Set `AUTH_SECRET` for API protection
2. **Database**: Consider PostgreSQL for production
3. **Monitoring**: Enable LangSmith tracing
4. **Scaling**: Use multiple uvicorn workers
5. **Caching**: Implement Redis for session storage

## Troubleshooting

### Common Issues

1. **Service won't start**
   - Check if ports 8080/8501 are available
   - Verify environment variables are set
   - Check database path permissions

2. **Analysis fails**
   - Ensure API keys are configured
   - Check network connectivity
   - Review logs for specific errors

3. **Frontend not connecting**
   - Verify `AGENT_URL` environment variable
   - Check FastAPI service is running
   - Confirm CORS settings

### Logs

```bash
# Service logs
tail -f logs/service.log

# Check service status
curl http://localhost:8080/health
```

## Support

For issues related to:
- **ASO Analysis**: Check existing agent implementation
- **Web Service**: Review FastAPI and Streamlit documentation
- **API Integration**: See `/docs` endpoint for OpenAPI spec