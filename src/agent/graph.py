from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import MessagesState, StateGraph


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


def generate_initial_keywords(state: State) -> State:
    ideas = state.ideas
    initial_keywords = [generate_initial_keywords(idea) for idea in ideas]
    return State(
        ideas=ideas,
        initial_keywords=initial_keywords
    )


graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node(generate_initial_keywords)
    .add_edge("__start__", "generate_initial_keywords")
    .compile(name="New Graph")
)
