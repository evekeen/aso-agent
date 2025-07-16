# ASO Agent Implementation Plan
## Recreating Agent-Service-Toolkit Architecture for ASO Analysis

### Table of Contents
1. [Overview](#overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Project Structure](#project-structure)
4. [Essential Components](#essential-components)
5. [Implementation Steps](#implementation-steps)
6. [Code Examples](#code-examples)
7. [ASO-Specific Adaptations](#aso-specific-adaptations)
8. [Dependencies](#dependencies)
9. [Environment Setup](#environment-setup)
10. [Deployment](#deployment)

---

## Overview

This document provides a comprehensive plan to recreate the agent-service-toolkit architecture for serving an ASO (App Store Optimization) analysis agent. The original ASO agent is a complex LangGraph workflow that analyzes app ideas, generates keywords, searches app stores, calculates market sizes, and provides difficulty analysis.

### Key Goals
- **Web Interface**: Create a Streamlit-based chat interface for ASO analysis
- **API Service**: FastAPI backend with streaming support for real-time progress updates
- **Progress Tracking**: Integrate existing progress tracking system with web UI
- **Data Persistence**: Maintain conversation history and cache ASO analysis results
- **Streaming**: Real-time updates during multi-step analysis process

---

## Architecture Diagrams

### High-Level Architecture
```
┌─────────────────┐    HTTP/WebSocket    ┌──────────────────┐
│   Streamlit UI  │ ◄──────────────────► │   FastAPI        │
│   (Frontend)    │                      │   Service        │
│                 │                      │   (Backend)      │
│ • Chat Interface│                      │ • Agent Executor │
│ • Progress View │                      │ • SSE Streaming  │
│ • Results Viz   │                      │ • Authentication │
└─────────────────┘                      └──────────────────┘
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
                                                   │
                                                   ▼
                                         ┌──────────────────┐
                                         │   Data Layer     │
                                         │                  │
                                         │ • SQLite Store   │
                                         │ • ASO Cache      │
                                         │ • Chat History   │
                                         └──────────────────┘
```

### Request Flow Diagram
```
User Input → Streamlit → HTTP Client → FastAPI → LangGraph Agent → External APIs
                                                       │
                                                       ▼
                                              Progress Updates
                                                       │
                                                       ▼
                                        SSE Stream ← FastAPI ← Agent Progress
                                                       │
                                                       ▼
                                          Streamlit ← Client ← Stream Parser
                                                       │
                                                       ▼
                                                  UI Updates
```

### Data Flow Architecture
```
┌─────────────────┐
│   User Input    │
│ "Analyze golf   │
│  app ideas"     │
└─────────────────┘
          │
          ▼
┌─────────────────┐
│ ASO Agent State │
│ • ideas: []     │
│ • keywords: {}  │
│ • revenue: {}   │
│ • difficulty: {}│
└─────────────────┘
          │
          ▼
┌─────────────────┐
│ Progress Stream │
│ • Node progress │
│ • Intermediate  │
│   results       │
│ • Final report  │
└─────────────────┘
```

---

## Project Structure

```
aso-agent/
├── pyproject.toml                 # Dependencies and project config
├── .env                          # Environment variables
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   └── settings.py           # Configuration management
│   ├── schema/
│   │   ├── __init__.py
│   │   └── schema.py             # Pydantic models
│   ├── service/
│   │   ├── __init__.py
│   │   └── service.py            # FastAPI server
│   ├── client/
│   │   ├── __init__.py
│   │   └── client.py             # HTTP client
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agents.py             # Agent registry
│   │   └── aso_agent.py          # ASO agent wrapper
│   ├── memory/
│   │   ├── __init__.py
│   │   └── sqlite.py             # Database persistence
│   ├── streamlit_app.py          # Frontend interface
│   └── run_service.py            # Server startup
├── lib/                          # Existing ASO libraries
│   ├── keywords.py
│   ├── sensor_tower.py
│   ├── appstore.py
│   └── aso_store.py
└── README.md
```

---

## Essential Components

### 1. FastAPI Service Architecture

The core service follows the agent-service-toolkit pattern with lifecycle management and streaming support.

#### Key Features:
- **Async Lifespan Management**: Initialize database and store connections
- **Bearer Token Authentication**: Optional API key protection
- **Server-Sent Events**: Real-time streaming for progress updates
- **Agent Execution**: Support for both invoke and stream modes
- **Error Handling**: Comprehensive exception management

#### Core Endpoints:
- `GET /info` - Service metadata and available agents
- `POST /invoke` - Single request-response execution
- `POST /stream` - Server-sent events streaming
- `POST /feedback` - User feedback collection
- `GET /health` - Health check

### 2. Streamlit Frontend

A chat-based interface optimized for ASO analysis workflows.

#### Key Features:
- **Real-time Chat**: Message-based interaction with agent
- **Progress Visualization**: Live updates during analysis phases
- **Results Display**: Structured presentation of ASO findings
- **Configuration Panel**: Agent and model selection
- **Session Management**: Persistent conversation threads

#### ASO-Specific UI Elements:
- **Keywords Table**: Interactive keyword analysis results
- **Market Size Charts**: Revenue visualization by keyword
- **Difficulty Scatter Plot**: Traffic vs. difficulty analysis
- **Export Options**: Download reports in various formats

### 3. Agent Integration Layer

Wrapper for the existing ASO LangGraph agent to work with the service architecture.

#### Key Responsibilities:
- **Graph Compilation**: Convert existing graph to service-compatible format
- **State Management**: Handle ASO-specific state schema
- **Progress Integration**: Bridge progress tracking with streaming
- **Configuration**: Accept runtime parameters for analysis

---

## Implementation Steps

### Phase 1: Foundation Setup
1. **Project Structure**: Create directory structure and basic files
2. **Dependencies**: Install required packages (FastAPI, Streamlit, LangGraph)
3. **Configuration**: Set up environment variables and settings
4. **Database Setup**: Initialize SQLite for conversation persistence

### Phase 2: Backend Development
1. **FastAPI Service**: Implement core server with lifespan management
2. **Schema Definition**: Create Pydantic models for ASO-specific data
3. **Agent Wrapper**: Adapt existing ASO graph for service architecture
4. **Streaming Implementation**: Add SSE support for progress updates

### Phase 3: Frontend Development
1. **Streamlit App**: Create chat interface with ASO-specific features
2. **HTTP Client**: Implement client for API communication
3. **Progress UI**: Add real-time progress visualization
4. **Results Display**: Create ASO analysis result components

### Phase 4: Integration & Testing
1. **End-to-End Testing**: Verify complete workflow
2. **Performance Optimization**: Optimize for large analysis workloads
3. **Error Handling**: Comprehensive error management
4. **Documentation**: Create user guides and API documentation

---

## Code Examples

### FastAPI Service Implementation

#### Server Setup and Lifespan Management
```python
# src/service/service.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing_extensions import Annotated
import json
import logging
from src.core.settings import settings
from src.agents.agents import get_agent, get_all_agent_info
from src.memory import initialize_database, initialize_store
from src.schema.schema import UserInput, StreamInput, ChatMessage

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Configurable lifespan that initializes the appropriate database checkpointer and store
    based on settings.
    """
    try:
        # Initialize both checkpointer (for short-term memory) and store (for long-term memory)
        async with initialize_database() as saver, initialize_store() as store:
            # Set up both components
            if hasattr(saver, "setup"):
                await saver.setup()
            if hasattr(store, "setup"):
                await store.setup()

            # Configure agents with both memory components
            agents = get_all_agent_info()
            for a in agents:
                agent = get_agent(a.key)
                agent.checkpointer = saver
                agent.store = store
            yield
    except Exception as e:
        logger.error(f"Error during database/store initialization: {e}")
        raise

def verify_bearer(
    http_auth: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(HTTPBearer(description="Please provide AUTH_SECRET api key.", auto_error=False)),
    ],
) -> None:
    if not settings.AUTH_SECRET:
        return
    auth_secret = settings.AUTH_SECRET.get_secret_value()
    if not http_auth or http_auth.credentials != auth_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

app = FastAPI(lifespan=lifespan)
router = APIRouter(dependencies=[Depends(verify_bearer)])
```

#### ASO Agent Execution Endpoints
```python
# src/service/service.py (continued)
@router.post("/aso-agent/invoke")
async def invoke_aso_agent(user_input: UserInput) -> ChatMessage:
    """
    Invoke ASO agent with user input to retrieve a final analysis report.
    """
    agent = get_agent("aso-agent")
    kwargs = {
        "input": {
            "messages": [HumanMessage(content=user_input.message)],
            "correlation_id": str(uuid.uuid4())
        },
        "config": {
            "configurable": {
                "model": user_input.model,
                "thread_id": user_input.thread_id,
                "user_id": user_input.user_id,
                **user_input.agent_config,
            }
        }
    }
    
    try:
        response_events = await agent.ainvoke(**kwargs, stream_mode=["updates", "values"])
        response_type, response = response_events[-1]
        
        if response_type == "values":
            # Extract final report from ASO agent state
            final_report = response.get("final_report", {})
            output = ChatMessage(
                type="ai",
                content=f"ASO Analysis Complete!\n\n{format_aso_report(final_report)}",
                custom_data={"final_report": final_report}
            )
        else:
            raise ValueError(f"Unexpected response type: {response_type}")
            
        return output
    except Exception as e:
        logger.error(f"ASO agent execution failed: {e}")
        raise HTTPException(status_code=500, detail="ASO analysis failed")

def format_aso_report(report: dict) -> str:
    """Format ASO analysis report for display."""
    if not report.get("app_ideas"):
        return "No analysis results available."
    
    formatted = []
    for idea, analysis in report["app_ideas"].items():
        market_size = analysis["best_possible_market_size_usd"]
        keyword_count = len(analysis["keywords"])
        
        formatted.append(f"**{idea.title()}**")
        formatted.append(f"• Market Size: ${market_size:,.2f}")
        formatted.append(f"• Keywords Analyzed: {keyword_count}")
        formatted.append("")
    
    return "\n".join(formatted)
```

#### Server-Sent Events Streaming
```python
# src/service/service.py (continued)
async def aso_message_generator(user_input: StreamInput) -> AsyncGenerator[str, None]:
    """
    Generate a stream of messages from the ASO agent with progress updates.
    """
    agent = get_agent("aso-agent")
    kwargs = {
        "input": {
            "messages": [HumanMessage(content=user_input.message)],
            "correlation_id": str(uuid.uuid4())
        },
        "config": {
            "configurable": {
                "model": user_input.model,
                "thread_id": user_input.thread_id,
                "user_id": user_input.user_id,
                **user_input.agent_config,
            }
        }
    }
    
    try:
        async for stream_event in agent.astream(**kwargs, stream_mode=["updates", "custom"]):
            if not isinstance(stream_event, tuple):
                continue
                
            stream_mode, event = stream_event
            
            if stream_mode == "updates":
                for node, updates in event.items():
                    if node.startswith("progress_"):
                        # Handle progress updates from ASO agent
                        progress_data = updates.get("progress", {})
                        yield f"data: {json.dumps({'type': 'progress', 'content': progress_data})}\n\n"
                    
                    elif updates.get("messages"):
                        # Handle regular message updates
                        for message in updates["messages"]:
                            chat_message = langchain_to_chat_message(message)
                            yield f"data: {json.dumps({'type': 'message', 'content': chat_message.model_dump()})}\n\n"
            
            elif stream_mode == "custom":
                # Handle custom events from ASO agent (intermediate results)
                if event.get("type") == "intermediate_result":
                    yield f"data: {json.dumps({'type': 'intermediate', 'content': event})}\n\n"
                    
    except Exception as e:
        logger.error(f"Error in ASO message generator: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'ASO analysis failed'})}\n\n"
    finally:
        yield "data: [DONE]\n\n"

@router.post("/aso-agent/stream", response_class=StreamingResponse)
async def stream_aso_agent(user_input: StreamInput) -> StreamingResponse:
    return StreamingResponse(
        aso_message_generator(user_input),
        media_type="text/event-stream",
    )
```

### Streamlit Frontend Implementation

#### Main App Structure
```python
# src/streamlit_app.py
import streamlit as st
import asyncio
import uuid
import os
from typing import AsyncGenerator
from src.client.client import AgentClient, AgentClientError
from src.schema.schema import ChatMessage
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

APP_TITLE = "ASO Analysis Agent"
APP_ICON = "📱"

def get_or_create_user_id() -> str:
    """Get or create a unique user ID."""
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    return st.session_state.user_id

async def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        menu_items={},
    )
    
    # Initialize client
    user_id = get_or_create_user_id()
    
    if "agent_client" not in st.session_state:
        agent_url = os.getenv("AGENT_URL", "http://localhost:8080")
        try:
            with st.spinner("Connecting to ASO analysis service..."):
                st.session_state.agent_client = AgentClient(base_url=agent_url)
        except AgentClientError as e:
            st.error(f"Error connecting to service: {e}")
            st.stop()
    
    agent_client = st.session_state.agent_client
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model selection
        model = st.selectbox(
            "LLM Model",
            options=agent_client.info.models,
            index=agent_client.info.models.index(agent_client.info.default_model)
        )
        
        # Analysis settings
        st.subheader("ASO Analysis Settings")
        market_threshold = st.number_input(
            "Market Size Threshold ($)",
            min_value=1000,
            max_value=1000000,
            value=50000,
            step=1000
        )
        
        keywords_per_idea = st.slider(
            "Keywords per App Idea",
            min_value=5,
            max_value=50,
            value=20
        )
        
        use_streaming = st.toggle("Stream Results", value=True)
        
        # Clear conversation
        if st.button("🗑️ Clear Conversation"):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
    
    # Main chat interface
    st.title(f"{APP_ICON} ASO Analysis Agent")
    st.markdown("**Analyze app ideas for App Store Optimization opportunities**")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message.type):
            st.write(message.content)
            
            # Display ASO-specific results
            if message.custom_data.get("final_report"):
                display_aso_results(message.custom_data["final_report"])
    
    # Chat input
    if user_input := st.chat_input("Describe your app ideas for ASO analysis..."):
        # Add user message
        user_message = ChatMessage(type="human", content=user_input)
        st.session_state.messages.append(user_message)
        
        with st.chat_message("human"):
            st.write(user_input)
        
        # Get agent response
        with st.chat_message("ai"):
            if use_streaming:
                await handle_streaming_response(
                    agent_client, user_input, model, 
                    market_threshold, keywords_per_idea
                )
            else:
                await handle_single_response(
                    agent_client, user_input, model,
                    market_threshold, keywords_per_idea
                )

async def handle_streaming_response(
    client: AgentClient, 
    message: str, 
    model: str, 
    market_threshold: int, 
    keywords_per_idea: int
) -> None:
    """Handle streaming response with progress updates."""
    
    # Create containers for different types of updates
    progress_container = st.empty()
    message_container = st.empty()
    results_container = st.empty()
    
    try:
        stream = client.astream(
            message=message,
            model=model,
            thread_id=st.session_state.thread_id,
            user_id=st.session_state.user_id,
            agent_config={
                "market_threshold": market_threshold,
                "keywords_per_idea": keywords_per_idea
            }
        )
        
        full_response = ""
        final_report = None
        
        async for event in stream:
            if event.get("type") == "progress":
                # Update progress bar
                progress_data = event["content"]
                update_progress_display(progress_container, progress_data)
                
            elif event.get("type") == "message":
                # Update main message
                message_data = event["content"]
                if message_data.get("content"):
                    full_response += message_data["content"]
                    message_container.markdown(full_response)
                
                # Check for final report
                if message_data.get("custom_data", {}).get("final_report"):
                    final_report = message_data["custom_data"]["final_report"]
                    
            elif event.get("type") == "intermediate":
                # Show intermediate results
                intermediate_data = event["content"]
                display_intermediate_results(results_container, intermediate_data)
        
        # Store final message
        ai_message = ChatMessage(
            type="ai",
            content=full_response,
            custom_data={"final_report": final_report} if final_report else {}
        )
        st.session_state.messages.append(ai_message)
        
        # Display final results
        if final_report:
            display_aso_results(final_report)
            
    except Exception as e:
        st.error(f"Error during ASO analysis: {e}")

def update_progress_display(container, progress_data: dict) -> None:
    """Update progress display with current analysis step."""
    node_name = progress_data.get("node_name", "")
    progress_pct = progress_data.get("progress_percentage", 0)
    status_message = progress_data.get("status_message", "")
    
    with container.container():
        st.subheader(f"🔄 {node_name.replace('_', ' ').title()}")
        st.progress(progress_pct / 100)
        if status_message:
            st.caption(status_message)

def display_intermediate_results(container, data: dict) -> None:
    """Display intermediate results during analysis."""
    result_type = data.get("result_type")
    
    with container.container():
        if result_type == "keywords_found":
            st.subheader("📝 Keywords Generated")
            keywords_data = data.get("keywords", {})
            for idea, keywords in keywords_data.items():
                st.write(f"**{idea}**: {', '.join(keywords[:5])}...")
                
        elif result_type == "apps_found":
            st.subheader("📱 Apps Found")
            apps_data = data.get("apps_by_keyword", {})
            total_apps = sum(len(apps) for apps in apps_data.values())
            st.metric("Total Apps Found", total_apps)
            
        elif result_type == "market_size_calculated":
            st.subheader("💰 Market Size Analysis")
            revenue_data = data.get("revenue_by_keyword", {})
            if revenue_data:
                df = pd.DataFrame([
                    {"Keyword": k, "Market Size ($)": v}
                    for k, v in revenue_data.items()
                ])
                st.dataframe(df, use_container_width=True)

def display_aso_results(final_report: dict) -> None:
    """Display comprehensive ASO analysis results."""
    st.subheader("📊 ASO Analysis Results")
    
    app_ideas = final_report.get("app_ideas", {})
    if not app_ideas:
        st.warning("No analysis results available.")
        return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "🎯 Keywords", "📊 Charts"])
    
    with tab1:
        display_overview_tab(app_ideas)
    
    with tab2:
        display_keywords_tab(app_ideas)
    
    with tab3:
        display_charts_tab(app_ideas)

def display_overview_tab(app_ideas: dict) -> None:
    """Display overview of all app ideas."""
    st.subheader("App Ideas Overview")
    
    overview_data = []
    for idea, analysis in app_ideas.items():
        overview_data.append({
            "App Idea": idea.title(),
            "Market Size ($)": f"${analysis['best_possible_market_size_usd']:,.2f}",
            "Keywords Analyzed": len(analysis['keywords']),
            "Avg Difficulty": calculate_avg_difficulty(analysis['keywords']),
            "Avg Traffic": calculate_avg_traffic(analysis['keywords'])
        })
    
    df = pd.DataFrame(overview_data)
    st.dataframe(df, use_container_width=True)

def display_keywords_tab(app_ideas: dict) -> None:
    """Display detailed keyword analysis."""
    st.subheader("Keyword Analysis")
    
    # App idea selector
    selected_idea = st.selectbox(
        "Select App Idea",
        options=list(app_ideas.keys()),
        format_func=lambda x: x.title()
    )
    
    if selected_idea:
        keywords = app_ideas[selected_idea]['keywords']
        
        # Convert to DataFrame for better display
        keywords_data = []
        for keyword, data in keywords.items():
            keywords_data.append({
                "Keyword": keyword,
                "Difficulty": data['difficulty_rating'],
                "Traffic": data['traffic_rating'],
                "Market Size ($)": f"${data['market_size_usd']:,.2f}",
                "Opportunity Score": calculate_opportunity_score(data)
            })
        
        df = pd.DataFrame(keywords_data)
        st.dataframe(df, use_container_width=True)
        
        # Export options
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Keywords CSV",
            data=csv,
            file_name=f"{selected_idea}_keywords.csv",
            mime="text/csv"
        )

def display_charts_tab(app_ideas: dict) -> None:
    """Display charts and visualizations."""
    st.subheader("Analysis Charts")
    
    # Prepare data for charts
    all_keywords = []
    for idea, analysis in app_ideas.items():
        for keyword, data in analysis['keywords'].items():
            all_keywords.append({
                "App Idea": idea.title(),
                "Keyword": keyword,
                "Difficulty": data['difficulty_rating'],
                "Traffic": data['traffic_rating'],
                "Market Size": data['market_size_usd']
            })
    
    if not all_keywords:
        st.warning("No keyword data available for charts.")
        return
    
    df = pd.DataFrame(all_keywords)
    
    # Market size by app idea
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Market Size by App Idea")
        market_by_idea = df.groupby("App Idea")["Market Size"].max().reset_index()
        fig1 = px.bar(
            market_by_idea,
            x="App Idea",
            y="Market Size",
            title="Best Market Opportunity per App Idea"
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("Difficulty vs Traffic")
        fig2 = px.scatter(
            df,
            x="Difficulty",
            y="Traffic",
            size="Market Size",
            color="App Idea",
            hover_data=["Keyword"],
            title="Keyword Difficulty vs Traffic Analysis"
        )
        st.plotly_chart(fig2, use_container_width=True)

def calculate_avg_difficulty(keywords: dict) -> float:
    """Calculate average difficulty score."""
    if not keywords:
        return 0.0
    difficulties = [data['difficulty_rating'] for data in keywords.values()]
    return sum(difficulties) / len(difficulties)

def calculate_avg_traffic(keywords: dict) -> float:
    """Calculate average traffic score."""
    if not keywords:
        return 0.0
    traffic_scores = [data['traffic_rating'] for data in keywords.values()]
    return sum(traffic_scores) / len(traffic_scores)

def calculate_opportunity_score(keyword_data: dict) -> float:
    """Calculate opportunity score based on traffic/difficulty ratio."""
    difficulty = keyword_data['difficulty_rating']
    traffic = keyword_data['traffic_rating']
    
    if difficulty == 0:
        return 0.0
    
    # Higher traffic, lower difficulty = better opportunity
    return (traffic / difficulty) * 100

if __name__ == "__main__":
    asyncio.run(main())
```

### Agent Integration Layer

#### ASO Agent Wrapper
```python
# src/agents/aso_agent.py
from typing import Dict, Any, AsyncGenerator
from dataclasses import dataclass
from src.agent.graph import graph as aso_graph, State as ASOState
from langgraph.graph import StateGraph
from langgraph.types import StreamWriter
import uuid
import json

@dataclass
class ASOAgentConfig:
    """Configuration for ASO agent execution."""
    market_threshold: int = 50000
    keywords_per_idea: int = 20
    max_apps_per_keyword: int = 20

class ASOAgentWrapper:
    """Wrapper for the ASO LangGraph agent to work with service architecture."""
    
    def __init__(self):
        self.graph = aso_graph
        self.config = ASOAgentConfig()
    
    async def ainvoke(self, input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ASO analysis and return final results."""
        
        # Extract configuration
        agent_config = config.get("configurable", {})
        self.config.market_threshold = agent_config.get("market_threshold", 50000)
        self.config.keywords_per_idea = agent_config.get("keywords_per_idea", 20)
        
        # Prepare initial state
        initial_state = {
            "messages": input_data.get("messages", []),
            "correlation_id": str(uuid.uuid4()),
            "ideas": [],
            "initial_keywords": {},
            "keywords": {},
            "apps_by_keyword": {},
            "apps_data_by_keyword": {},
            "revenue_by_app": {},
            "revenue_by_keyword": {},
            "traffic_by_keyword": {},
            "difficulty_by_keyword": {},
            "filtered_keywords": [],
            "final_report": {}
        }
        
        # Execute graph
        result = await self.graph.ainvoke(initial_state, config)
        
        return {
            "messages": result.get("messages", []),
            "final_report": result.get("final_report", {}),
            "correlation_id": result.get("correlation_id", "")
        }
    
    async def astream(
        self, 
        input_data: Dict[str, Any], 
        config: Dict[str, Any],
        stream_mode: list[str] = None
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """Stream ASO analysis with progress updates."""
        
        # Extract configuration
        agent_config = config.get("configurable", {})
        self.config.market_threshold = agent_config.get("market_threshold", 50000)
        self.config.keywords_per_idea = agent_config.get("keywords_per_idea", 20)
        
        # Prepare initial state
        initial_state = {
            "messages": input_data.get("messages", []),
            "correlation_id": str(uuid.uuid4()),
            "ideas": [],
            "initial_keywords": {},
            "keywords": {},
            "apps_by_keyword": {},
            "apps_data_by_keyword": {},
            "revenue_by_app": {},
            "revenue_by_keyword": {},
            "traffic_by_keyword": {},
            "difficulty_by_keyword": {},
            "filtered_keywords": [],
            "final_report": {}
        }
        
        # Stream execution with progress tracking
        async for event in self.graph.astream(
            initial_state, 
            config, 
            stream_mode=stream_mode or ["updates", "values", "custom"]
        ):
            if isinstance(event, tuple):
                stream_type, data = event
                
                # Handle progress updates from @with_progress_tracking decorators
                if stream_type == "custom" and data.get("type") == "progress":
                    yield ("custom", {
                        "type": "progress",
                        "node_name": data.get("node_name", ""),
                        "progress_percentage": data.get("progress_percentage", 0),
                        "status_message": data.get("status_message", "")
                    })
                
                # Handle intermediate results
                elif stream_type == "updates":
                    for node_name, updates in data.items():
                        if node_name == "search_apps_for_keywords" and updates.get("apps_by_keyword"):
                            yield ("custom", {
                                "type": "intermediate_result",
                                "result_type": "apps_found",
                                "apps_by_keyword": updates["apps_by_keyword"]
                            })
                        
                        elif node_name == "generate_initial_keywords" and updates.get("initial_keywords"):
                            yield ("custom", {
                                "type": "intermediate_result",
                                "result_type": "keywords_found",
                                "keywords": updates["initial_keywords"]
                            })
                        
                        elif node_name == "get_keyword_total_market_size" and updates.get("revenue_by_keyword"):
                            yield ("custom", {
                                "type": "intermediate_result",
                                "result_type": "market_size_calculated",
                                "revenue_by_keyword": updates["revenue_by_keyword"]
                            })
                
                # Pass through other events
                else:
                    yield event
            else:
                yield event

# Create the wrapped agent instance
aso_agent = ASOAgentWrapper()
```

#### Agent Registry
```python
# src/agents/agents.py
from dataclasses import dataclass
from typing import Dict
from src.agents.aso_agent import aso_agent
from src.schema.schema import AgentInfo

@dataclass
class Agent:
    description: str
    graph: any

# Registry of available agents
agents: Dict[str, Agent] = {
    "aso-agent": Agent(
        description="ASO (App Store Optimization) analysis agent that analyzes app ideas, generates keywords, calculates market sizes, and provides difficulty analysis.",
        graph=aso_agent
    )
}

def get_agent(agent_id: str):
    """Get agent instance by ID."""
    if agent_id not in agents:
        raise ValueError(f"Agent '{agent_id}' not found. Available agents: {list(agents.keys())}")
    return agents[agent_id].graph

def get_all_agent_info() -> list[AgentInfo]:
    """Get information about all available agents."""
    return [
        AgentInfo(key=agent_id, description=agent.description)
        for agent_id, agent in agents.items()
    ]
```

### HTTP Client Implementation

```python
# src/client/client.py
import httpx
import json
import os
from typing import AsyncGenerator, Dict, Any, Optional
from src.schema.schema import UserInput, StreamInput, ChatMessage, ServiceMetadata

class AgentClientError(Exception):
    """Exception raised by the agent client."""
    pass

class AgentClient:
    """Client for interacting with the ASO agent service."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        agent: str = "aso-agent",
        timeout: float = 300.0,  # 5 minutes for long ASO analyses
        get_info: bool = True,
    ):
        self.base_url = base_url.rstrip('/')
        self.agent = agent
        self.timeout = timeout
        self.auth_secret = os.getenv("AUTH_SECRET")
        self.info: Optional[ServiceMetadata] = None
        
        if get_info:
            self.retrieve_info()
    
    @property
    def _headers(self) -> Dict[str, str]:
        """Get headers for requests."""
        headers = {"Content-Type": "application/json"}
        if self.auth_secret:
            headers["Authorization"] = f"Bearer {self.auth_secret}"
        return headers
    
    def retrieve_info(self) -> None:
        """Retrieve service metadata."""
        try:
            response = httpx.get(
                f"{self.base_url}/info",
                headers=self._headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.info = ServiceMetadata.model_validate(response.json())
        except httpx.HTTPError as e:
            raise AgentClientError(f"Error getting service info: {e}")
    
    async def ainvoke(
        self,
        message: str,
        model: str = "gpt-4o-mini",
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """Invoke the ASO agent with a single request."""
        
        user_input = UserInput(
            message=message,
            model=model,
            thread_id=thread_id,
            user_id=user_id,
            agent_config=agent_config or {}
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/{self.agent}/invoke",
                    json=user_input.model_dump(),
                    headers=self._headers,
                )
                response.raise_for_status()
                return ChatMessage.model_validate(response.json())
            except httpx.HTTPError as e:
                raise AgentClientError(f"Error invoking agent: {e}")
    
    async def astream(
        self,
        message: str,
        model: str = "gpt-4o-mini",
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        stream_tokens: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses from the ASO agent."""
        
        stream_input = StreamInput(
            message=message,
            model=model,
            thread_id=thread_id,
            user_id=user_id,
            agent_config=agent_config or {},
            stream_tokens=stream_tokens
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/{self.agent}/stream",
                    json=stream_input.model_dump(),
                    headers=self._headers,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        parsed = self._parse_stream_line(line)
                        if parsed is not None:
                            yield parsed
                            
            except httpx.HTTPError as e:
                raise AgentClientError(f"Error streaming from agent: {e}")
    
    def _parse_stream_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single line from the SSE stream."""
        line = line.strip()
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                return None
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                raise AgentClientError(f"Error parsing stream data: {e}")
        return None
```

### Schema Definitions

```python
# src/schema/schema.py
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime

class UserInput(BaseModel):
    """Input for ASO agent analysis."""
    
    message: str = Field(
        description="User input describing app ideas for ASO analysis.",
        examples=["Analyze these app ideas: golf shot tracker, sleep monitoring app"]
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="LLM model to use for analysis."
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID for conversation persistence."
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID for cross-session persistence."
    )
    agent_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for ASO analysis",
        examples=[{
            "market_threshold": 50000,
            "keywords_per_idea": 20,
            "max_apps_per_keyword": 20
        }]
    )

class StreamInput(UserInput):
    """Input for streaming ASO analysis."""
    
    stream_tokens: bool = Field(
        default=True,
        description="Whether to stream tokens in real-time."
    )

class ToolCall(BaseModel):
    """Tool call information."""
    
    name: str = Field(description="Name of the tool called")
    args: Dict[str, Any] = Field(description="Arguments passed to the tool")
    id: str = Field(description="Unique identifier for the tool call")

class ChatMessage(BaseModel):
    """Message in the chat conversation."""
    
    type: Literal["human", "ai", "tool", "custom"] = Field(
        description="Type of message",
        examples=["human", "ai", "tool", "custom"]
    )
    content: str = Field(
        description="Content of the message",
        examples=["Analyze golf app ideas", "ASO analysis complete!"]
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="Tool calls made in this message"
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="ID of tool call this message responds to"
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Run ID for tracing"
    )
    response_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata"
    )
    custom_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom data like ASO analysis results"
    )

class AgentInfo(BaseModel):
    """Information about an available agent."""
    
    key: str = Field(description="Agent identifier")
    description: str = Field(description="Agent description")

class ServiceMetadata(BaseModel):
    """Service metadata including available agents and models."""
    
    agents: List[AgentInfo] = Field(description="Available agents")
    models: List[str] = Field(description="Available LLM models")
    default_agent: str = Field(description="Default agent")
    default_model: str = Field(description="Default model")

class ChatHistory(BaseModel):
    """Chat conversation history."""
    
    messages: List[ChatMessage] = Field(description="Messages in conversation")
    thread_id: str = Field(description="Thread identifier")
    user_id: Optional[str] = Field(description="User identifier")

class Feedback(BaseModel):
    """User feedback on agent responses."""
    
    run_id: str = Field(description="Run ID of the response")
    rating: int = Field(description="Rating (1-5 stars)")
    comment: Optional[str] = Field(description="Optional feedback comment")
    user_id: Optional[str] = Field(description="User identifier")

# ASO-specific models
class KeywordAnalysis(BaseModel):
    """Analysis results for a single keyword."""
    
    difficulty_rating: float = Field(description="Difficulty score (0-100)")
    traffic_rating: float = Field(description="Traffic score (0-100)")
    market_size_usd: float = Field(description="Market size in USD")

class AppIdeaAnalysis(BaseModel):
    """Analysis results for an app idea."""
    
    best_possible_market_size_usd: float = Field(
        description="Best possible market size for this app idea"
    )
    keywords: Dict[str, KeywordAnalysis] = Field(
        description="Analysis for each keyword"
    )

class ASOAnalysisReport(BaseModel):
    """Complete ASO analysis report."""
    
    timestamp: datetime = Field(description="Analysis timestamp")
    analysis_metadata: Dict[str, Any] = Field(
        description="Metadata about the analysis"
    )
    app_ideas: Dict[str, AppIdeaAnalysis] = Field(
        description="Analysis results for each app idea"
    )
```

---

## ASO-Specific Adaptations

### Progress Tracking Integration

The existing ASO agent uses `@with_progress_tracking` decorators. These need to be adapted to work with the streaming architecture:

```python
# src/agent/progress_middleware.py (adapted)
from typing import Any, Dict, Callable
from functools import wraps
import asyncio

class ProgressContext:
    """Context for streaming progress updates."""
    
    def __init__(self, node_name: str, total_items: int = 100):
        self.node_name = node_name
        self.total_items = total_items
        self.current_item = 0
        self.stream_writer = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.stream_writer:
            await self.stream_writer.awrite({
                "type": "progress",
                "node_name": self.node_name,
                "progress_percentage": 100,
                "status_message": "Completed"
            })
    
    async def update(self, current: int, message: str = ""):
        """Update progress and stream to client."""
        self.current_item = current
        progress_pct = (current / self.total_items) * 100
        
        if self.stream_writer:
            await self.stream_writer.awrite({
                "type": "progress",
                "node_name": self.node_name,
                "progress_percentage": progress_pct,
                "status_message": message
            })

def with_progress_tracking(node_name: str, description: str):
    """Decorator to add progress tracking to ASO agent nodes."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract stream writer from context if available
            config = kwargs.get("config", {})
            stream_writer = config.get("stream_writer")
            
            if stream_writer:
                await stream_writer.awrite({
                    "type": "progress",
                    "node_name": node_name,
                    "progress_percentage": 0,
                    "status_message": f"Starting {description}"
                })
            
            try:
                result = await func(*args, **kwargs)
                
                if stream_writer:
                    await stream_writer.awrite({
                        "type": "progress",
                        "node_name": node_name,
                        "progress_percentage": 100,
                        "status_message": f"Completed {description}"
                    })
                
                return result
            except Exception as e:
                if stream_writer:
                    await stream_writer.awrite({
                        "type": "progress",
                        "node_name": node_name,
                        "progress_percentage": 0,
                        "status_message": f"Error: {str(e)}"
                    })
                raise
        
        return wrapper
    return decorator
```

### ASO Store Integration

The existing ASO store needs to be compatible with the service architecture:

```python
# src/memory/aso_store.py (adapted)
from lib.aso_store import get_aso_store, ASONamespaces
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_aso_store_context():
    """Context manager for ASO store that integrates with service lifecycle."""
    store = get_aso_store()
    try:
        # Setup if needed
        if hasattr(store, 'setup'):
            await store.setup()
        yield store
    finally:
        # Cleanup if needed
        if hasattr(store, 'cleanup'):
            await store.cleanup()
```

---

## Dependencies

### Core Dependencies
```toml
# pyproject.toml
[project]
name = "aso-agent-service"
version = "0.1.0"
description = "Web service for ASO analysis agent"
dependencies = [
    # Web framework
    "fastapi ~= 0.115.5",
    "uvicorn[standard] ~= 0.32.1",
    "streamlit ~= 1.40.1",
    
    # HTTP client
    "httpx ~= 0.27.2",
    
    # LangGraph and LangChain
    "langgraph ~= 0.2.6",
    "langgraph-checkpoint-sqlite ~= 2.0.1",
    "langchain-core ~= 0.3.33",
    "langchain-openai ~= 0.3.0",
    
    # Data processing
    "pydantic ~= 2.10.1",
    "pydantic-settings ~= 2.6.1",
    "pandas ~= 2.2.0",
    
    # Async support
    "aiosqlite ~= 0.20.0",
    "aiohttp ~= 3.9.0",
    
    # Visualization
    "plotly ~= 5.17.0",
    
    # Environment
    "python-dotenv ~= 1.0.1",
    
    # Existing ASO dependencies
    "requests ~= 2.31.0",
    "beautifulsoup4 ~= 4.12.0",
]

[project.optional-dependencies]
dev = [
    "pytest ~= 7.4.0",
    "pytest-asyncio ~= 0.21.0",
    "black ~= 23.0.0",
    "isort ~= 5.12.0",
    "mypy ~= 1.5.0",
]
```

### Installation Script
```bash
#!/bin/bash
# setup.sh

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install project with dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Create necessary directories
mkdir -p data/cache
mkdir -p logs

echo "Setup complete! Activate environment with: source .venv/bin/activate"
```

---

## Environment Setup

### Environment Variables
```bash
# .env
# LLM Configuration
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
DEFAULT_MODEL=gpt-4o-mini

# Service Configuration
HOST=0.0.0.0
PORT=8080
AUTH_SECRET=your-secret-key-here

# Database Configuration
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=data/aso_agent.db

# ASO-specific APIs
SENSOR_TOWER_API_KEY=your-sensor-tower-key
ASO_MOBILE_API_KEY=your-aso-mobile-key

# Monitoring (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=aso-agent-service

# Streamlit Configuration
AGENT_URL=http://localhost:8080
```

### Settings Configuration
```python
# src/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from typing import Optional, Literal
from enum import Enum

class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MONGO = "mongo"

class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Service configuration
    HOST: str = Field(default="0.0.0.0", description="Service host")
    PORT: int = Field(default=8080, description="Service port")
    AUTH_SECRET: Optional[SecretStr] = Field(default=None, description="API authentication secret")
    
    # Database configuration
    DATABASE_TYPE: DatabaseType = Field(default=DatabaseType.SQLITE, description="Database type")
    SQLITE_DB_PATH: str = Field(default="data/aso_agent.db", description="SQLite database path")
    
    # LLM configuration
    OPENAI_API_KEY: Optional[SecretStr] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[SecretStr] = Field(default=None, description="Anthropic API key")
    DEFAULT_MODEL: str = Field(default="gpt-4o-mini", description="Default LLM model")
    
    # ASO-specific configuration
    SENSOR_TOWER_API_KEY: Optional[SecretStr] = Field(default=None, description="Sensor Tower API key")
    ASO_MOBILE_API_KEY: Optional[SecretStr] = Field(default=None, description="ASO Mobile API key")
    
    # Analysis defaults
    DEFAULT_MARKET_THRESHOLD: int = Field(default=50000, description="Default market size threshold")
    DEFAULT_KEYWORDS_PER_IDEA: int = Field(default=20, description="Default keywords per app idea")
    DEFAULT_MAX_APPS: int = Field(default=20, description="Default max apps per keyword")
    
    # Monitoring
    LANGCHAIN_TRACING_V2: bool = Field(default=False, description="Enable LangSmith tracing")
    LANGCHAIN_API_KEY: Optional[SecretStr] = Field(default=None, description="LangSmith API key")
    LANGCHAIN_PROJECT: str = Field(default="aso-agent-service", description="LangSmith project name")
    
    @property
    def available_models(self) -> list[str]:
        """Get list of available LLM models based on API keys."""
        models = []
        if self.OPENAI_API_KEY:
            models.extend(["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
        if self.ANTHROPIC_API_KEY:
            models.extend(["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"])
        return models or ["gpt-4o-mini"]  # Fallback

# Global settings instance
settings = Settings()
```

---

## Deployment

### Local Development
```bash
# Start the service
python src/run_service.py

# In another terminal, start Streamlit
streamlit run src/streamlit_app.py
```

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .
RUN pip install -e .

# Copy source code
COPY src/ ./src/
COPY lib/ ./lib/

# Create data directory
RUN mkdir -p data

# Expose ports
EXPOSE 8080 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Default command (can be overridden)
CMD ["python", "src/run_service.py"]
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  aso-agent-service:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SENSOR_TOWER_API_KEY=${SENSOR_TOWER_API_KEY}
      - ASO_MOBILE_API_KEY=${ASO_MOBILE_API_KEY}
      - HOST=0.0.0.0
      - PORT=8080
    volumes:
      - ./data:/app/data
    command: ["python", "src/run_service.py"]
    
  aso-streamlit:
    build: .
    ports:
      - "8501:8501"
    environment:
      - AGENT_URL=http://aso-agent-service:8080
    depends_on:
      - aso-agent-service
    command: ["streamlit", "run", "src/streamlit_app.py", "--server.address=0.0.0.0"]

volumes:
  data:
```

### Production Considerations

1. **Security**:
   - Use proper authentication (AUTH_SECRET)
   - Enable HTTPS with reverse proxy
   - Secure API keys in environment variables

2. **Performance**:
   - Use PostgreSQL for production database
   - Implement caching for frequently accessed data
   - Consider horizontal scaling for high load

3. **Monitoring**:
   - Enable LangSmith tracing for debugging
   - Add application metrics and logging
   - Set up health checks and alerting

4. **Reliability**:
   - Implement graceful shutdown
   - Add retry logic for external API calls
   - Use connection pooling for database

---

## Summary

This implementation plan provides a complete blueprint for recreating the agent-service-toolkit architecture specifically for the ASO analysis agent. The key components include:

1. **FastAPI Backend**: Robust service with streaming support and lifecycle management
2. **Streamlit Frontend**: Interactive chat interface with ASO-specific visualizations
3. **Agent Integration**: Seamless integration with existing ASO LangGraph workflow
4. **Progress Tracking**: Real-time updates during multi-step analysis
5. **Data Persistence**: Conversation history and analysis result caching
6. **Production Ready**: Security, monitoring, and deployment considerations

The architecture maintains the flexibility and robustness of the original toolkit while adding ASO-specific features like keyword analysis tables, market size visualizations, and structured report generation.