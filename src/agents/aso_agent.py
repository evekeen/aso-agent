"""ASO Agent wrapper for web service integration."""

from typing import Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass
import uuid
import json
import asyncio
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from src.agent.graph import graph as aso_graph, State as ASOState
from src.schema.schema import ChatMessage, ProgressUpdate, IntermediateResult
from lib.progress_tracker import get_progress_tracker
from lib.correlation_id import set_correlation_id, get_correlation_id


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
        initial_state = self._prepare_initial_state(input_data, agent_config)
        
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
        initial_state = self._prepare_initial_state(input_data, agent_config)
        
        # Set up progress tracking
        correlation_id = initial_state.get("correlation_id")
        if correlation_id:
            set_correlation_id(correlation_id)
        
        # Track progress events
        progress_tracker = get_progress_tracker()
        last_progress = {}
        
        # Stream execution with progress tracking
        async for event in self.graph.astream(
            initial_state, 
            config, 
            stream_mode=stream_mode or ["updates", "values"]
        ):
            if isinstance(event, tuple):
                stream_type, data = event
                
                # Handle state updates
                if stream_type == "updates":
                    for node_name, updates in data.items():
                        # Handle interrupts
                        if node_name == "__interrupt__":
                            for interrupt in updates:
                                interrupt_message = self._convert_to_chat_message(
                                    AIMessage(content=interrupt.value)
                                )
                                yield ("message", interrupt_message)
                                yield ("interrupt", {"message": interrupt.value})
                            continue
                            
                        if not updates:
                            continue
                            
                        # Handle progress updates
                        async for progress_event in self._handle_progress_updates(
                            node_name, updates, correlation_id, progress_tracker, last_progress
                        ):
                            yield progress_event
                        
                        # Handle intermediate results
                        async for intermediate_event in self._handle_intermediate_results(node_name, updates):
                            yield intermediate_event
                        
                        # Handle messages
                        if updates.get("messages"):
                            for message in updates["messages"]:
                                yield ("message", self._convert_to_chat_message(message))
                
                # Handle final values
                elif stream_type == "values":
                    final_report = data.get("final_report")
                    if final_report:
                        # Create final response message
                        final_message = AIMessage(
                            content=self._format_final_report(final_report)
                        )
                        chat_message = self._convert_to_chat_message(final_message)
                        chat_message.custom_data = {"final_report": final_report}
                        yield ("message", chat_message)
                
                # Pass through other events
                else:
                    yield event
            else:
                yield ("raw", event)
    
    def _prepare_initial_state(self, input_data: Dict[str, Any], agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare initial state for ASO analysis."""
        messages = input_data.get("messages", [])
        correlation_id = str(uuid.uuid4())
        
        return {
            "messages": messages,
            "correlation_id": correlation_id,
            "ideas": [],  # Will be extracted by collect_app_ideas node
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
    
    async def _handle_progress_updates(
        self, 
        node_name: str, 
        updates: Dict[str, Any], 
        correlation_id: str,
        progress_tracker,
        last_progress: Dict[str, float]
    ):
        """Handle progress updates from nodes."""
        try:
            # Get current progress from tracker
            if correlation_id:
                task_progress = await progress_tracker.get_task_progress(correlation_id)
                if task_progress:
                    current_progress = 0
                    for step in task_progress.get("workflow_steps", []):
                        if step["name"] == node_name:
                            current_progress = step.get("progress_percentage", 0)
                            break
                    
                    # Only yield if progress changed significantly
                    if abs(current_progress - last_progress.get(node_name, 0)) > 5:
                        last_progress[node_name] = current_progress
                        yield ("progress", ProgressUpdate(
                            node_name=node_name,
                            progress_percentage=current_progress,
                            status_message=f"Processing {node_name.replace('_', ' ').title()}",
                            correlation_id=correlation_id
                        ).model_dump())
        except Exception as e:
            print(f"Error handling progress updates: {e}")
    
    async def _handle_intermediate_results(self, node_name: str, updates: Dict[str, Any]):
        """Handle intermediate results from nodes."""
        try:
            if node_name == "generate_initial_keywords" and updates.get("initial_keywords"):
                yield ("intermediate", IntermediateResult(
                    result_type="keywords_found",
                    data={"keywords": updates["initial_keywords"]}
                ).model_dump())
            
            elif node_name == "search_apps_for_keywords" and updates.get("apps_by_keyword"):
                total_apps = sum(len(apps) for apps in updates["apps_by_keyword"].values())
                yield ("intermediate", IntermediateResult(
                    result_type="apps_found",
                    data={
                        "apps_by_keyword": updates["apps_by_keyword"],
                        "total_apps": total_apps
                    }
                ).model_dump())
            
            elif node_name == "get_keyword_total_market_size" and updates.get("revenue_by_keyword"):
                yield ("intermediate", IntermediateResult(
                    result_type="market_size_calculated",
                    data={"revenue_by_keyword": updates["revenue_by_keyword"]}
                ).model_dump())
                
        except Exception as e:
            print(f"Error handling intermediate results: {e}")
    
    def _convert_to_chat_message(self, message) -> ChatMessage:
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
            custom_data={}
        )
    
    def _format_final_report(self, final_report: Dict[str, Any]) -> str:
        """Format ASO analysis report for display."""
        if not final_report.get("app_ideas"):
            return "ASO Analysis Complete! No specific results available."
        
        formatted = ["🎯 **ASO Analysis Results**\n"]
        
        for idea, analysis in final_report["app_ideas"].items():
            market_size = analysis.get("best_possible_market_size_usd", 0)
            keyword_count = len(analysis.get("keywords", {}))
            
            formatted.append(f"**{idea.title()}**")
            formatted.append(f"• Best Market Opportunity: ${market_size:,.2f}")
            formatted.append(f"• Keywords Analyzed: {keyword_count}")
            
            # Show top 3 keywords by market size
            keywords = analysis.get("keywords", {})
            if keywords:
                top_keywords = sorted(
                    keywords.items(),
                    key=lambda x: x[1].get("market_size_usd", 0),
                    reverse=True
                )[:3]
                
                formatted.append("• Top Keywords:")
                for keyword, data in top_keywords:
                    market = data.get("market_size_usd", 0)
                    difficulty = data.get("difficulty_rating", 0)
                    formatted.append(f"  - '{keyword}': ${market:,.0f} (difficulty: {difficulty})")
            
            formatted.append("")
        
        return "\n".join(formatted)


# Create the wrapped agent instance
aso_agent = ASOAgentWrapper()