from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, List
from pydantic import BaseModel, Field

from langgraph.graph import MessagesState, StateGraph
from langgraph.types import interrupt
from langchain_openai import ChatOpenAI


class Configuration(TypedDict):
    pass


class KeywordList(BaseModel):
    """List of ASO keywords"""
    keywords: List[str] = Field(description="List of 5 long-tail keywords for App Store optimization")


@dataclass
class State(MessagesState):
    ideas: list[str]
    initial_keywords: dict[str, list[str]]
    keywords: dict[str, list[str]]
    apps_by_keyword: dict[str, list[str]]
    revenue_by_app: dict[str, float]
    revenue_by_keyword: dict[str, float]
    traffic_by_keyword: dict[str, float]
    difficulty_by_keyword: dict[str, float]


def collect_app_ideas_node(state: dict) -> dict:
    return {"ideas": ["golf shot tracer", "snoring tracker"]}


def generate_initial_keywords_node(state: dict) -> dict:
    """LangGraph node to generate initial keywords for app ideas using LLM."""
    ideas = state.get("ideas", [])
    if not ideas:
        raise ValueError("No app ideas provided for keyword generation.")
    
    print(f"Processing {len(ideas)} app ideas for keyword generation...")
    
    # Initialize LLM with structured output
    try:
        llm = ChatOpenAI(model='gpt-4o-mini').with_structured_output(KeywordList)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize OpenAI LLM: {e}")
    
    initial_keywords = {}
    failed_ideas = []
    
    for idea in ideas:
        prompt = f"""You are a professional ASO specialist to optimize apps on the Apple AppStore. 
        Generate exactly 5 long-tail keywords for the idea: {idea}
        
        Focus on keywords that:
        - Are specific and long-tail (2-3 words)
        - Target the app's main functionality
        - Include relevant user intent
        - Are competitive for App Store search
        """
        
        try:
            response = llm.invoke(prompt)
            
            # Validate the response
            if not response.keywords or len(response.keywords) != 5:
                raise ValueError(f"LLM returned invalid keywords for '{idea}': expected 5 keywords, got {len(response.keywords) if response.keywords else 0}")
            
            # Validate each keyword
            for keyword in response.keywords:
                if not keyword or not isinstance(keyword, str) or len(keyword.strip()) == 0:
                    raise ValueError(f"Invalid keyword generated for '{idea}': empty or non-string keyword")
            
            initial_keywords[idea] = response.keywords
            print(f"Generated keywords for '{idea}': {response.keywords}")
            
        except Exception as e:
            failed_ideas.append(idea)
            print(f"Failed to generate keywords for '{idea}': {e}")
            # Continue processing other ideas, but track failures
    
    # If all ideas failed, throw an error
    if len(failed_ideas) == len(ideas):
        raise RuntimeError(f"Failed to generate keywords for all {len(ideas)} app ideas. No keywords were generated.")
    
    # If some ideas failed, throw an error with details
    if failed_ideas:
        raise RuntimeError(f"Failed to generate keywords for {len(failed_ideas)} out of {len(ideas)} app ideas: {failed_ideas}")
    
    return {"initial_keywords": initial_keywords}


# Note: In LangGraph Cloud/API, persistence is handled automatically by the platform
# No need to provide a custom checkpointer as it will be ignored when deployed

graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node("collect_app_ideas", collect_app_ideas_node)
    .add_node("generate_initial_keywords", generate_initial_keywords_node)
    .add_edge("__start__", "collect_app_ideas")
    .add_edge("collect_app_ideas", "generate_initial_keywords")
    .compile(name="ASO Researcher")
)
