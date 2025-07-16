"""Schema definitions for ASO Agent Service."""

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


class ProgressUpdate(BaseModel):
    """Progress update during ASO analysis."""
    
    node_name: str = Field(description="Current processing node")
    progress_percentage: float = Field(description="Progress percentage (0-100)")
    status_message: str = Field(description="Current status message")
    correlation_id: Optional[str] = Field(description="Analysis correlation ID")


class IntermediateResult(BaseModel):
    """Intermediate result during analysis."""
    
    result_type: str = Field(description="Type of intermediate result")
    data: Dict[str, Any] = Field(description="Result data")
    timestamp: datetime = Field(default_factory=datetime.now)


class StreamEvent(BaseModel):
    """Event in the analysis stream."""
    
    type: Literal["message", "progress", "intermediate", "error", "complete"] = Field(
        description="Type of stream event"
    )
    content: Dict[str, Any] = Field(description="Event content")
    timestamp: datetime = Field(default_factory=datetime.now)