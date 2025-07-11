from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, List, Literal
from datetime import datetime
from langgraph.graph import MessagesState, StateGraph
from langgraph.types import Command
from lib.keywords import generate_keywords
from lib.sensor_tower import get_apps_revenue
from lib.appstore import search_app_store
from lib.keyword_difficulty import analyze_keyword_difficulty_from_appstore_apps
from lib.aso_store import get_aso_store, ASONamespaces


class Configuration(TypedDict):
    pass


@dataclass
class State(MessagesState):
    ideas: list[str]
    initial_keywords: dict[str, list[str]]
    keywords: dict[str, list[str]]
    apps_by_keyword: dict[str, list[str]]
    apps_data_by_keyword: dict[str, list]
    revenue_by_app: dict[str, float]
    revenue_by_keyword: dict[str, float]
    traffic_by_keyword: dict[str, float]
    difficulty_by_keyword: dict[str, float]
    filtered_keywords: list[str]
    final_report: dict


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


async def search_apps_for_keywords(state: dict) -> dict:
    """
    LangGraph node to search App Store for apps using generated keywords.
    
    This node:
    1. Takes keywords from initial_keywords
    2. Searches App Store for each keyword
    3. Returns apps_by_keyword mapping
    """
    initial_keywords = state.get("initial_keywords", {})
    if not initial_keywords:
        raise ValueError("No initial keywords found. Please run keyword generation first.")
    
    # Flatten all keywords from all ideas
    all_keywords = []
    for idea, keywords in initial_keywords.items():
        all_keywords.extend(keywords)
    
    # Remove duplicates while preserving order
    unique_keywords = list(dict.fromkeys(all_keywords))
    
    if not unique_keywords:
        raise ValueError("No keywords found to search for apps.")
    
    print(f"Searching App Store for {len(unique_keywords)} unique keywords...")
    
    apps_by_keyword = {}
    apps_data_by_keyword = {}
    failed_keywords = []
    
    # Get store instance
    store = get_aso_store()
    
    # Search for apps using each keyword
    for keyword in unique_keywords:
        # Check store first
        item = await store.aget(ASONamespaces.keyword_apps(), keyword.lower())
        cached_app_ids = item.value["app_ids"] if item else []
        
        if cached_app_ids:
            print(f"Using cached apps for keyword: '{keyword}' ({len(cached_app_ids)} apps)")
            apps_by_keyword[keyword] = cached_app_ids
            # We'll need to fetch full app data when needed for difficulty analysis
            apps_data_by_keyword[keyword] = []  # Will be populated later if needed
        else:
            try:
                print(f"Searching for apps with keyword: '{keyword}'")
                
                # Search App Store for this keyword
                apps = await search_app_store(keyword, country="us", num=20)
                
                if not apps:
                    print(f"No apps found for keyword: '{keyword}'")
                    apps_by_keyword[keyword] = []
                    apps_data_by_keyword[keyword] = []
                else:
                    # Extract app IDs from AppstoreApp objects
                    app_ids = [app.app_id for app in apps]
                    apps_by_keyword[keyword] = app_ids
                    apps_data_by_keyword[keyword] = apps
                    
                    # Cache the keyword-app associations
                    await store.aput(
                        ASONamespaces.keyword_apps(),
                        keyword.lower(),
                        {"app_ids": app_ids}
                    )
                    
                    print(f"Found {len(app_ids)} apps for '{keyword}': {app_ids[:3]}{'...' if len(app_ids) > 3 else ''}")
                    
            except Exception as e:
                failed_keywords.append(keyword)
                print(f"Failed to search for keyword '{keyword}': {e}")
                apps_by_keyword[keyword] = []
                apps_data_by_keyword[keyword] = []
    
    # Calculate statistics
    total_apps = sum(len(app_ids) for app_ids in apps_by_keyword.values())
    successful_keywords = len([k for k, v in apps_by_keyword.items() if v])
    
    print(f"\n📊 App Search Results:")
    print(f"  • Keywords processed: {len(unique_keywords)}")
    print(f"  • Keywords with apps: {successful_keywords}")
    print(f"  • Total apps found: {total_apps}")
    
    if failed_keywords:
        print(f"  • Failed keywords: {len(failed_keywords)}")
        print(f"    {failed_keywords}")
    
    # Validate results
    if not any(apps_by_keyword.values()):
        raise RuntimeError("No apps found for any keywords. Cannot proceed with market analysis.")
    
    if len(failed_keywords) == len(unique_keywords):
        raise RuntimeError("Failed to search for all keywords. Check your network connection and try again.")
    
    return {"apps_by_keyword": apps_by_keyword, "apps_data_by_keyword": apps_data_by_keyword}


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


def filter_keywords_by_market_size(state: dict) -> Command[Literal["analyze_keyword_difficulty", "generate_final_report"]]:
    """
    Filter keywords by market size threshold before expensive difficulty analysis.
    
    Routes to:
    - analyze_keyword_difficulty: if keywords meet market size threshold
    - generate_final_report: if no keywords meet threshold
    """
    revenue_by_keyword = state.get("revenue_by_keyword", {})
    apps_data_by_keyword = state.get("apps_data_by_keyword", {})
    
    if not revenue_by_keyword:
        raise ValueError("No revenue data found. Please run market size analysis first.")
    
    # Filter keywords with market size > $50K
    threshold = 50000
    filtered_keywords = [
        keyword for keyword, revenue in revenue_by_keyword.items() 
        if revenue >= threshold
    ]
    
    print(f"\n💰 Market Size Filtering Results:")
    print(f"  • Total keywords analyzed: {len(revenue_by_keyword)}")
    print(f"  • Threshold: ${threshold:,}")
    print(f"  • Keywords meeting threshold: {len(filtered_keywords)}")
    
    if filtered_keywords:
        print(f"  • High-value keywords: {', '.join(filtered_keywords[:5])}{'...' if len(filtered_keywords) > 5 else ''}")
        
        # Filter apps_data_by_keyword to only include high-value keywords
        filtered_apps_data = {
            keyword: apps_data_by_keyword.get(keyword, [])
            for keyword in filtered_keywords
        }
        
        return Command(
            update={
                "filtered_keywords": filtered_keywords,
                "apps_data_by_keyword": filtered_apps_data
            },
            goto="analyze_keyword_difficulty"
        )
    else:
        print("  • No keywords meet the market size threshold")
        print("  • Skipping difficulty analysis and generating report with available data")
        
        return Command(
            update={
                "filtered_keywords": [],
                "difficulty_by_keyword": {}
            },
            goto="generate_final_report"
        )


async def analyze_keyword_difficulty(state: dict) -> dict:
    """
    LangGraph node to analyze keyword difficulty using the iTunes algorithm.
    
    This node:
    1. Gets app data for each keyword from apps_data_by_keyword
    2. Runs keyword difficulty analysis for each keyword
    3. Returns difficulty scores by keyword
    """
    apps_data_by_keyword = state.get("apps_data_by_keyword", {})
    if not apps_data_by_keyword:
        raise ValueError("No apps data found. Please run app search first.")
    
    print(f"Analyzing keyword difficulty for {len(apps_data_by_keyword)} keywords...")
    
    difficulty_by_keyword = {}
    failed_keywords = []
    
    for keyword, apps in apps_data_by_keyword.items():
        try:
            if not apps:
                print(f"No apps available for keyword '{keyword}', skipping difficulty analysis")
                difficulty_by_keyword[keyword] = 1.0
                continue
            
            print(f"Analyzing difficulty for keyword: '{keyword}' ({len(apps)} apps)")
            
            # Run difficulty analysis
            result = await analyze_keyword_difficulty_from_appstore_apps(keyword, apps)
            difficulty_by_keyword[keyword] = result.score
            
            # Log detailed results
            difficulty_level = "Easy" if result.score <= 3 else "Medium" if result.score <= 6 else "Hard" if result.score <= 8 else "Very Hard"
            print(f"  '{keyword}': {result.score}/10 ({difficulty_level})")
            print(f"    Title matches: {result.title_matches.score:.1f}, Competitors: {result.competitors}")
            print(f"    Installs: {result.installs_score:.1f}, Rating: {result.rating_score:.1f}, Age: {result.age_score:.1f}")
            
        except Exception as e:
            failed_keywords.append(keyword)
            print(f"Failed to analyze difficulty for keyword '{keyword}': {e}")
            difficulty_by_keyword[keyword] = 5.0
    
    # Calculate statistics
    if difficulty_by_keyword:
        avg_difficulty = sum(difficulty_by_keyword.values()) / len(difficulty_by_keyword)
        easy_keywords = len([k for k, v in difficulty_by_keyword.items() if v <= 3])
        medium_keywords = len([k for k, v in difficulty_by_keyword.items() if 3 < v <= 6])
        hard_keywords = len([k for k, v in difficulty_by_keyword.items() if v > 6])
        
        print(f"\n🎯 Keyword Difficulty Summary:")
        print(f"  • Average difficulty: {avg_difficulty:.2f}/10")
        print(f"  • Easy keywords (≤3): {easy_keywords}")
        print(f"  • Medium keywords (3-6): {medium_keywords}")
        print(f"  • Hard keywords (>6): {hard_keywords}")
        
        if failed_keywords:
            print(f"  • Failed analyses: {len(failed_keywords)}")
    
    return {"difficulty_by_keyword": difficulty_by_keyword}


async def generate_final_report(state: dict) -> dict:
    """
    Generate ASO analysis report structured for agent consumption.
    
    Report format for each app idea:
    1. Best possible market size
    2. Dictionary of all keywords with difficulty, traffic, and market size ratings
    """
    ideas = state.get("ideas", [])
    revenue_by_keyword = state.get("revenue_by_keyword", {})
    difficulty_by_keyword = state.get("difficulty_by_keyword", {})
    initial_keywords = state.get("initial_keywords", {})
    
    print(f"\n📊 Generating Final ASO Analysis Report for Agent Consumption...")
    
    # Generate structured report for each app idea
    app_analysis = {}
    
    for idea in ideas:
        # Get keywords related to this idea
        idea_keywords = initial_keywords.get(idea, [])
        
        if not idea_keywords:
            app_analysis[idea] = {
                "best_possible_market_size_usd": 0,
                "keywords": {}
            }
            continue
        
        # Calculate best possible market size (maximum value of all keywords for this idea)
        keyword_market_sizes = [
            revenue_by_keyword.get(keyword, 0) 
            for keyword in idea_keywords
        ]
        best_possible_market_size = max(keyword_market_sizes) if keyword_market_sizes else 0
        
        # Build keyword dictionary with all metrics
        keywords_data = {}
        for keyword in idea_keywords:
            market_size = revenue_by_keyword.get(keyword, 0)
            difficulty_score = difficulty_by_keyword.get(keyword, 5.0)  # Default to medium difficulty
            traffic_rating = 1.0  # Placeholder value as requested
            
            keywords_data[keyword] = {
                "difficulty_rating": round(difficulty_score, 2),
                "traffic_rating": traffic_rating,
                "market_size_usd": market_size
            }
        
        app_analysis[idea] = {
            "best_possible_market_size_usd": best_possible_market_size,
            "keywords": keywords_data
        }
    
    # Calculate overall statistics for logging
    total_keywords_analyzed = len(revenue_by_keyword)
    total_market_size = sum(revenue_by_keyword.values())
    difficulty_analyses_completed = len(difficulty_by_keyword)
    
    # Get store statistics
    store = get_aso_store()
    store_stats = await store.get_stats()
    
    # Structure final report for agent consumption
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "analysis_metadata": {
            "total_keywords_analyzed": total_keywords_analyzed,
            "difficulty_analyses_completed": difficulty_analyses_completed,
            "total_market_size_usd": total_market_size,
            "store_usage": {
                "active_items": store_stats.get('active_items', 0),
                "total_items": store_stats.get('total_items', 0),
                "namespaces": store_stats.get('namespaces', 0)
            }
        },
        "app_ideas": app_analysis
    }
    
    # Print summary for monitoring
    print(f"✅ Agent-Ready Report Generated!")
    print(f"  • App ideas analyzed: {len(ideas)}")
    print(f"  • Keywords evaluated: {total_keywords_analyzed}")
    print(f"  • Difficulty analyses: {difficulty_analyses_completed}")
    print(f"  • Total market opportunity: ${total_market_size:,.2f}")
    print(f"  • Store efficiency: {store_stats.get('active_items', 0)} active items across {store_stats.get('namespaces', 0)} namespaces")
    
    # Print structured data for each app idea
    for idea, analysis in app_analysis.items():
        keywords_count = len(analysis['keywords'])
        best_market = analysis['best_possible_market_size_usd']
        
        print(f"\n🎯 {idea.title()}:")
        print(f"  • Best possible market size: ${best_market:,.2f}")
        print(f"  • Total keywords: {keywords_count}")
        
        if keywords_count > 0:
            # Show top 3 keywords by market size
            top_keywords = sorted(
                analysis['keywords'].items(), 
                key=lambda x: x[1]['market_size_usd'], 
                reverse=True
            )[:3]
            
            print(f"  • Top keywords by market size:")
            for keyword, data in top_keywords:
                print(f"    - '{keyword}': ${data['market_size_usd']:,.0f} (difficulty: {data['difficulty_rating']})")
    
    return {"final_report": final_report}


graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node("collect_app_ideas", collect_app_ideas)
    .add_node("generate_initial_keywords", generate_initial_keywords)
    .add_node("search_apps_for_keywords", search_apps_for_keywords)
    .add_node("get_keyword_total_market_size", get_keyword_total_market_size)
    .add_node("filter_keywords_by_market_size", filter_keywords_by_market_size)
    .add_node("analyze_keyword_difficulty", analyze_keyword_difficulty)
    .add_node("generate_final_report", generate_final_report)
    .add_edge("__start__", "collect_app_ideas")
    .add_edge("collect_app_ideas", "generate_initial_keywords")
    .add_edge("generate_initial_keywords", "search_apps_for_keywords")
    .add_edge("search_apps_for_keywords", "get_keyword_total_market_size")
    .add_edge("get_keyword_total_market_size", "filter_keywords_by_market_size")
    .add_edge("analyze_keyword_difficulty", "generate_final_report")
    .compile(name="ASO Researcher")
)
