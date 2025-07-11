from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, List, Literal
from langgraph.graph import MessagesState, StateGraph
from langgraph.types import Command
from lib.keywords import generate_keywords
from lib.sensor_tower import get_apps_revenue
from lib.appstore import search_app_store
from lib.keyword_difficulty import analyze_keyword_difficulty_from_appstore_apps


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
    
    # Search for apps using each keyword
    for keyword in unique_keywords:
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
            result = analyze_keyword_difficulty_from_appstore_apps(keyword, apps)
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


def generate_final_report(state: dict) -> dict:
    """
    Generate comprehensive ASO analysis report with market opportunities and keyword recommendations.
    """
    ideas = state.get("ideas", [])
    revenue_by_keyword = state.get("revenue_by_keyword", {})
    difficulty_by_keyword = state.get("difficulty_by_keyword", {})
    filtered_keywords = state.get("filtered_keywords", [])
    
    print(f"\n📊 Generating Final ASO Analysis Report...")
    
    # Calculate market opportunity score for each keyword
    keyword_opportunities = []
    for keyword in revenue_by_keyword.keys():
        revenue = revenue_by_keyword.get(keyword, 0)
        difficulty = difficulty_by_keyword.get(keyword, 10)  # Default to high difficulty if not analyzed
        
        # Opportunity score: higher revenue, lower difficulty = better opportunity
        # Formula: (revenue / 100000) * (11 - difficulty) to balance revenue and difficulty
        opportunity_score = (revenue / 100000) * (11 - difficulty)
        
        keyword_opportunities.append({
            "keyword": keyword,
            "market_size_usd": revenue,
            "difficulty_score": difficulty,
            "opportunity_score": round(opportunity_score, 2),
            "analyzed": keyword in difficulty_by_keyword
        })
    
    # Sort by opportunity score
    keyword_opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    
    # Generate recommendations for each app idea
    app_recommendations = {}
    for idea in ideas:
        # Get keywords related to this idea from initial_keywords if available
        initial_keywords = state.get("initial_keywords", {})
        idea_keywords = initial_keywords.get(idea, [])
        
        # Filter opportunities for this idea's keywords
        idea_opportunities = [
            opp for opp in keyword_opportunities 
            if opp["keyword"] in idea_keywords
        ]
        
        # Get top 10 opportunities for this idea
        top_opportunities = idea_opportunities[:10]
        
        # Calculate total market size for this idea
        total_market = sum(opp["market_size_usd"] for opp in idea_opportunities)
        
        # Categorize keywords by difficulty
        easy_keywords = [opp for opp in idea_opportunities if opp["difficulty_score"] <= 3]
        medium_keywords = [opp for opp in idea_opportunities if 3 < opp["difficulty_score"] <= 6]
        hard_keywords = [opp for opp in idea_opportunities if opp["difficulty_score"] > 6]
        
        app_recommendations[idea] = {
            "total_market_size_usd": total_market,
            "total_keywords": len(idea_opportunities),
            "analyzed_keywords": len([opp for opp in idea_opportunities if opp["analyzed"]]),
            "top_opportunities": top_opportunities,
            "difficulty_breakdown": {
                "easy": len(easy_keywords),
                "medium": len(medium_keywords),
                "hard": len(hard_keywords)
            }
        }
    
    # Overall statistics
    total_keywords_analyzed = len(revenue_by_keyword)
    high_value_keywords = len(filtered_keywords)
    total_market_size = sum(revenue_by_keyword.values())
    
    final_report = {
        "analysis_summary": {
            "total_app_ideas": len(ideas),
            "total_keywords_analyzed": total_keywords_analyzed,
            "high_value_keywords": high_value_keywords,
            "total_market_size_usd": total_market_size,
            "difficulty_analyses_completed": len(difficulty_by_keyword)
        },
        "app_recommendations": app_recommendations,
        "top_overall_opportunities": keyword_opportunities[:20]
    }
    
    # Print summary
    print(f"✅ Report Generated Successfully!")
    print(f"  • App ideas analyzed: {len(ideas)}")
    print(f"  • Keywords evaluated: {total_keywords_analyzed}")
    print(f"  • High-value keywords (>${50000:,}+): {high_value_keywords}")
    print(f"  • Total market opportunity: ${total_market_size:,.2f}")
    
    # Print top opportunities for each app
    for idea, rec in app_recommendations.items():
        print(f"\n🎯 {idea.title()}:")
        print(f"  • Market size: ${rec['total_market_size_usd']:,.2f}")
        print(f"  • Top keyword: {rec['top_opportunities'][0]['keyword'] if rec['top_opportunities'] else 'None'}")
        print(f"  • Difficulty breakdown: {rec['difficulty_breakdown']['easy']} easy, {rec['difficulty_breakdown']['medium']} medium, {rec['difficulty_breakdown']['hard']} hard")
    
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
