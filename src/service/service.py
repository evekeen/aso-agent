"""FastAPI service for ASO Agent."""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Annotated

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from langchain_core.messages import HumanMessage, AIMessage

from src.service.settings import settings
from src.agents.agents import get_agent, get_all_agent_info
from src.memory import initialize_database, initialize_store
from src.schema.schema import (
    UserInput, 
    StreamInput, 
    ChatMessage, 
    ServiceMetadata,
    ChatHistory,
    Feedback
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_AGENT = "aso-agent"


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
                # Note: The current ASO agent doesn't directly use checkpointer/store
                # but we keep this pattern for future compatibility
                if hasattr(agent, 'checkpointer'):
                    agent.checkpointer = saver
                if hasattr(agent, 'store'):
                    agent.store = store
            
            logger.info("ASO Agent service initialized successfully")
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
    """Verify bearer token if AUTH_SECRET is configured."""
    if not settings.AUTH_SECRET:
        return
    auth_secret = settings.AUTH_SECRET.get_secret_value()
    if not http_auth or http_auth.credentials != auth_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


# Create FastAPI app
app = FastAPI(
    title="ASO Agent Service",
    description="Web service for ASO (App Store Optimization) analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create router with optional authentication
from fastapi import APIRouter
router = APIRouter(dependencies=[Depends(verify_bearer)])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aso-agent"}


@app.get("/info")
async def get_info() -> ServiceMetadata:
    """Get service metadata including available agents and models."""
    agents = get_all_agent_info()
    available_models = settings.available_models
    
    return ServiceMetadata(
        agents=agents,
        models=available_models,
        default_agent=DEFAULT_AGENT,
        default_model=settings.DEFAULT_MODEL
    )


async def _handle_input(user_input: UserInput, agent) -> tuple[dict, str]:
    """Prepare input for agent execution."""
    run_id = str(uuid.uuid4())
    
    # Convert user input to LangChain message
    human_message = HumanMessage(content=user_input.message)
    
    kwargs = {
        "input": {
            "messages": [human_message],
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
    
    return kwargs, run_id


def langchain_to_chat_message(message) -> ChatMessage:
    """Convert LangChain message to ChatMessage."""
    if hasattr(message, 'content'):
        content = message.content
    else:
        content = str(message)
    
    if hasattr(message, 'type'):
        msg_type = message.type
    elif isinstance(message, HumanMessage):
        msg_type = "human"
    elif isinstance(message, AIMessage):
        msg_type = "ai"
    else:
        msg_type = "custom"
    
    return ChatMessage(
        type=msg_type,
        content=content,
        tool_calls=[],
        custom_data=getattr(message, 'custom_data', {})
    )


@router.post("/{agent_id}/invoke")
@router.post("/invoke")
async def invoke(user_input: UserInput, agent_id: str = DEFAULT_AGENT) -> ChatMessage:
    """
    Invoke an agent with user input to retrieve a final response.
    """
    agent = get_agent(agent_id)
    kwargs, run_id = await _handle_input(user_input, agent)

    try:
        # Execute the agent
        result = await agent.ainvoke(**kwargs)
        
        # Extract the final message
        messages = result.get("messages", [])
        final_report = result.get("final_report", {})
        
        if messages:
            output = langchain_to_chat_message(messages[-1])
        else:
            # Create a response from the final report
            content = _format_aso_report(final_report) if final_report else "ASO analysis completed."
            output = ChatMessage(
                type="ai",
                content=content,
                custom_data={"final_report": final_report}
            )
        
        output.run_id = run_id
        return output
        
    except Exception as e:
        logger.error(f"An exception occurred during agent invocation: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during ASO analysis")


def _format_aso_report(report: dict) -> str:
    """Format ASO analysis report for display."""
    if not report.get("app_ideas"):
        return "ASO Analysis Complete! No specific results available."
    
    formatted = ["🎯 **ASO Analysis Results**\n"]
    
    for idea, analysis in report["app_ideas"].items():
        market_size = analysis.get("best_possible_market_size_usd", 0)
        keyword_count = len(analysis.get("keywords", {}))
        
        formatted.append(f"**{idea.title()}**")
        formatted.append(f"• Best Market Opportunity: ${market_size:,.2f}")
        formatted.append(f"• Keywords Analyzed: {keyword_count}")
        formatted.append("")
    
    return "\n".join(formatted)


async def message_generator(
    user_input: StreamInput, agent_id: str = DEFAULT_AGENT
) -> AsyncGenerator[str, None]:
    """
    Generate a stream of messages from the agent.
    """
    agent = get_agent(agent_id)
    kwargs, run_id = await _handle_input(user_input, agent)

    try:
        # Process streamed events from the agent
        async for stream_event in agent.astream(
            **kwargs, stream_mode=["updates", "values"]
        ):
            if not isinstance(stream_event, tuple):
                continue
                
            stream_mode, event = stream_event
            
            if stream_mode == "message":
                # Handle direct message events
                try:
                    if isinstance(event, dict) and "run_id" not in event:
                        event["run_id"] = run_id
                    yield f"data: {json.dumps({'type': 'message', 'content': event})}\n\n"
                except Exception as e:
                    logger.error(f"Error processing message event: {e}")
                    continue
            
            elif stream_mode == "progress":
                # Handle progress updates
                try:
                    yield f"data: {json.dumps({'type': 'progress', 'content': event})}\n\n"
                except Exception as e:
                    logger.error(f"Error processing progress event: {e}")
                    continue
            
            elif stream_mode == "intermediate":
                # Handle intermediate results
                try:
                    yield f"data: {json.dumps({'type': 'intermediate', 'content': event})}\n\n"
                except Exception as e:
                    logger.error(f"Error processing intermediate event: {e}")
                    continue
            
            elif stream_mode == "values":
                # Handle final values
                try:
                    final_report = event.get("final_report")
                    if final_report:
                        content = _format_aso_report(final_report)
                        chat_message = ChatMessage(
                            type="ai",
                            content=content,
                            custom_data={"final_report": final_report},
                            run_id=run_id
                        )
                        yield f"data: {json.dumps({'type': 'message', 'content': chat_message.model_dump()})}\n\n"
                except Exception as e:
                    logger.error(f"Error processing final values: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error in message generator: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'ASO analysis failed'})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


@router.post("/{agent_id}/stream", response_class=StreamingResponse)
@router.post("/stream", response_class=StreamingResponse)
async def stream(user_input: StreamInput, agent_id: str = DEFAULT_AGENT) -> StreamingResponse:
    """Stream responses from the agent."""
    return StreamingResponse(
        message_generator(user_input, agent_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.post("/feedback")
async def record_feedback(feedback: Feedback):
    """Record user feedback."""
    # TODO: Implement feedback storage
    logger.info(f"Received feedback: {feedback}")
    return {"status": "success", "message": "Feedback recorded"}


@router.get("/history/{thread_id}")
async def get_history(thread_id: str) -> ChatHistory:
    """Get conversation history for a thread."""
    # TODO: Implement history retrieval from checkpointer
    logger.info(f"History requested for thread: {thread_id}")
    return ChatHistory(
        messages=[],
        thread_id=thread_id,
        user_id=None
    )


# Include the router
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.service.service:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )