from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, List
from langgraph.graph import MessagesState, StateGraph
from lib.keywords import generate_keywords
from lib.sensor_tower import get_apps_revenue
from lib.appstore import search_app_store


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


async def get_keyword_total_market_size(state: dict) -> dict:
    """
    LangGraph node to analyze market size for keywords by fetching app revenues.
    
    This node:
    1. Gets apps for each keyword from apps_by_keyword
    2. Fetches revenue data for all apps using Sensor Tower API
    3. Calculates total market size per keyword
    4. Returns revenue data by app and by keyword
    """
    apps_by_keyword = state.get("apps_by_keyword", {})
    if not apps_by_keyword:
        raise ValueError("No apps by keyword data found. Please run app search first.")
    
    # Collect all unique app IDs
    all_app_ids = set()
    for keyword, app_ids in apps_by_keyword.items():
        all_app_ids.update(app_ids)
    
    all_app_ids = list(all_app_ids)
    
    if not all_app_ids:
        raise ValueError("No app IDs found for market size analysis.")
    
    print(f"Analyzing market size for {len(all_app_ids)} apps across {len(apps_by_keyword)} keywords...")
    
    try:
        # Fetch revenue data for all apps
        revenue_results = await get_apps_revenue(all_app_ids)
        
        # Process results and calculate metrics
        revenue_by_app = {}
        failed_apps = []
        
        for app_id, result in revenue_results.items():
            if isinstance(result, str):
                # Error message
                failed_apps.append(app_id)
                print(f"Failed to get revenue for app {app_id}: {result}")
            else:
                # Successful result
                revenue_by_app[app_id] = result.last_month_revenue_usd
                print(f"App {app_id} ({result.app_name}): {result.last_month_revenue_string}")
        
        # Calculate total market size per keyword
        revenue_by_keyword = {}
        for keyword, app_ids in apps_by_keyword.items():
            total_revenue = 0.0
            successful_apps = 0
            
            for app_id in app_ids:
                if app_id in revenue_by_app:
                    total_revenue += revenue_by_app[app_id]
                    successful_apps += 1
            
            revenue_by_keyword[keyword] = total_revenue
            print(f"Keyword '{keyword}': ${total_revenue:,.2f} total market size ({successful_apps}/{len(app_ids)} apps)")
        
        # Warn about failed apps but don't fail the entire process
        if failed_apps:
            print(f"Warning: Failed to get revenue data for {len(failed_apps)} apps: {failed_apps}")
        
        if not revenue_by_app:
            raise RuntimeError("Failed to get revenue data for any apps. Cannot calculate market size.")
        
        return {
            "revenue_by_app": revenue_by_app,
            "revenue_by_keyword": revenue_by_keyword
        }
        
    except Exception as e:
        raise RuntimeError(f"Market size analysis failed: {e}")


graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node("collect_app_ideas", collect_app_ideas)
    .add_node("generate_initial_keywords", generate_initial_keywords)
    .add_node("get_keyword_total_market_size", get_keyword_total_market_size)
    .add_edge("__start__", "collect_app_ideas")
    .add_edge("collect_app_ideas", "generate_initial_keywords")
    # Note: get_keyword_total_market_size requires apps_by_keyword data
    # This edge would be added after implementing the app search functionality
    # .add_edge("some_app_search_node", "get_keyword_total_market_size")
    .compile(name="ASO Researcher")
)
