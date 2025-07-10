from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict
from langgraph.graph import MessagesState, StateGraph
from lib.keywords import generate_keywords


class Configuration(TypedDict):
    pass


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


def collect_app_ideas(state: dict) -> dict:
    return {"ideas": ["golf shot tracer", "snoring tracker"]}


def generate_initial_keywords(state: dict) -> dict:
    """LangGraph node to generate initial keywords for app ideas using LLM."""
    ideas = state.get("ideas", [])
    if not ideas:
        raise ValueError("No app ideas provided for keyword generation.")
    
    print(f"Processing {len(ideas)} app ideas for keyword generation...")
    initial_keywords = generate_keywords(ideas, keywords_len=20)
    if not initial_keywords:
        raise RuntimeError("No keywords were generated for the provided app ideas.")
    
    return {"initial_keywords": initial_keywords}


graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node("collect_app_ideas", collect_app_ideas)
    .add_node("generate_initial_keywords", generate_initial_keywords)
    .add_node("get_keyword_total_market_size", get_keyword_total_market_size)
    .add_edge("__start__", "collect_app_ideas")
    .add_edge("collect_app_ideas", "generate_initial_keywords")
    .compile(name="ASO Researcher")
)
