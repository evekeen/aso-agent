from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, List, Literal
from datetime import datetime
from langgraph.graph import MessagesState, StateGraph
from langgraph.types import Command
from lib.keywords import generate_keywords
from lib.sensor_tower import get_apps_revenue
from lib.appstore import search_app_store
from lib.aso_store import get_aso_store, ASONamespaces
from src.agent.progress_middleware import with_progress_tracking, update_node_progress, ProgressContext


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
    correlation_id: str = ""


@with_progress_tracking("collect_app_ideas", "Collecting app ideas for ASO analysis")
async def collect_app_ideas(state: dict) -> dict:
    """Extract app ideas from user messages using LLM-based content extraction."""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    from langgraph.errors import NodeInterrupt
    from pydantic import BaseModel, Field
    from typing import Optional
    
    messages = state.get("messages", [])
    
    # Get the user's conversation history
    user_messages = []
    for msg in messages:
        if hasattr(msg, 'type') and msg.type == "human":
            user_messages.append(msg.content)
        elif isinstance(msg, HumanMessage):
            user_messages.append(msg.content)
    
    if not user_messages:
        # No user message found - ask for input
        raise NodeInterrupt(
            "I need you to describe the app ideas you want me to analyze. For example:\n\n" +
            "• 'Analyze fitness tracking apps'\n" +
            "• 'I want to explore meditation and sleep apps'\n" +
            "• 'What about productivity apps for students?'\n" +
            "• 'Investigate cooking and recipe apps'\n\n" +
            "What type of apps would you like me to research?"
        )
    
    # Combine all user messages for context
    full_conversation = " ".join(user_messages)
    latest_message = user_messages[-1]
    
    # Define structured output for app idea extraction and assessment
    class AppIdeasAssessment(BaseModel):
        """Assessment of app ideas from user message."""
        confidence: int = Field(
            description="Confidence level (1-10) that clear, specific app ideas can be extracted from the user's message",
            ge=1, le=10
        )
        app_ideas: Optional[List[str]] = Field(
            description="List of specific app ideas extracted (2-4 words each). Only provide if confidence >= 6.",
            default=None
        )
        needs_clarification: bool = Field(
            description="Whether the user's intent needs clarification to proceed with meaningful analysis"
        )
        follow_up_question: Optional[str] = Field(
            description="Specific follow-up question to ask the user if clarification is needed",
            default=None
        )
        reasoning: str = Field(
            description="Explanation of the assessment and why clarification may be needed"
        )
    
    # Create LLM with structured output
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        assessor = llm.with_structured_output(AppIdeasAssessment)
        
        # System prompt for app idea assessment
        system_prompt = """You are an expert at assessing whether user messages contain clear app ideas for ASO (App Store Optimization) analysis.

        Your task is to:
        1. Assess whether the user's message contains specific, analyzable app ideas
        2. Extract clear app ideas if they exist
        3. Identify when clarification is needed for meaningful analysis
        
        Do not think of new ideas, just takes exactly what was provided by the user. It must be one idea if user only talked abot on idea.

        HIGH CONFIDENCE (7-10): Clear, specific app ideas that can be immediately analyzed
        - "Analyze fitness tracking apps" → ["fitness tracker", "workout planner"]
        - "Sleep and meditation apps for anxiety" → ["meditation app", "sleep tracker", "anxiety relief app"]
        - "I want to research cooking apps with meal planning" → ["recipe app", "meal planner"]

        MEDIUM CONFIDENCE (4-6): General direction but needs more specificity
        - "I'm interested in health apps" → Needs clarification: which type of health apps?
        - "Apps for my business" → Needs clarification: what type of business?
        - "Something with social features" → Needs clarification: what purpose/category?

        LOW CONFIDENCE (1-3): Vague, unclear, or no app ideas mentioned
        - "Hello" → Needs clarification about app analysis intent
        - "What can you do?" → Needs clarification about specific app ideas
        - "I have an idea" → Needs clarification about the actual idea

        Rules for follow-up questions:
        - Be specific and helpful
        - Offer examples in the question
        - Guide toward actionable app categories
        - Keep questions conversational and encouraging"""
        
        # Assess the user's message
        update_node_progress(50.0, "Analyzing user message for app ideas")
        
        assessment = await assessor.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User's full conversation: {full_conversation}\n\nLatest message: {latest_message}")
        ])
        
        print(f"🔍 Assessment confidence: {assessment.confidence}/10")
        print(f"💭 Reasoning: {assessment.reasoning}")
        
        # Handle based on confidence level
        if assessment.confidence >= 6 and assessment.app_ideas:
            app_ideas = assessment.app_ideas
            print(f"📱 Extracted app ideas: {app_ideas}")
            update_node_progress(100.0, f"Successfully extracted {len(app_ideas)} app ideas")
            return {"ideas": app_ideas}
        
        elif assessment.needs_clarification and assessment.follow_up_question:
            print(f"❓ Asking for clarification: {assessment.follow_up_question}")
            raise NodeInterrupt(assessment.follow_up_question)
        
        else:
            # Generic clarification if assessment didn't provide a specific question
            clarification_msg = (
                "I need more specific information about the apps you want me to analyze. "
                "Could you tell me more about:\n\n"
                "• What type of apps are you interested in? (e.g., fitness, productivity, entertainment)\n"
                "• What problem should these apps solve?\n"
                "• Who is the target audience?\n\n"
                "For example: 'fitness apps for runners' or 'productivity tools for students'"
            )
            print(f"❓ Asking for generic clarification")
            raise NodeInterrupt(clarification_msg)
        
    except Exception as e:
        print(f"❌ Error during app idea assessment: {e}")
        # Ask for clarification instead of falling back
        error_msg = (
            "I had trouble understanding your request. Could you please describe the specific "
            "app ideas you'd like me to analyze?\n\n"
            "Examples:\n"
            "• 'Analyze meditation and mindfulness apps'\n"
            "• 'I want to research fitness tracking applications'\n"
            "• 'Explore productivity apps for remote workers'"
        )
        raise NodeInterrupt(error_msg)


@with_progress_tracking("generate_initial_keywords", "Generating initial keywords using LLM")
def generate_initial_keywords(state: dict) -> dict:
    """LangGraph node to generate initial keywords for app ideas using LLM."""
    ideas = state.get("ideas", [])
    if not ideas:
        raise ValueError("No app ideas provided for keyword generation.")
    
    update_node_progress(25.0, "Analyzing app ideas for keyword generation")
    initial_keywords = generate_keywords(ideas, keywords_len=20)
    
    if not initial_keywords:
        raise RuntimeError("No keywords were generated for the provided app ideas.")
    
    update_node_progress(100.0, f"Generated keywords for {len(initial_keywords)} app ideas")
    return {"initial_keywords": initial_keywords}


@with_progress_tracking("search_apps_for_keywords", "Searching App Store for relevant apps")
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
    update_node_progress(10.0, f"Starting App Store search for {len(unique_keywords)} keywords")
    
    apps_by_keyword = {}
    apps_data_by_keyword = {}
    failed_keywords = []
    
    # Get store instance
    store = get_aso_store()
    
    # Search for apps using each keyword
    async with ProgressContext("search_apps_for_keywords", len(unique_keywords)) as progress:
        for i, keyword in enumerate(unique_keywords):
            await progress.update(i, f"Processing keyword: '{keyword}'")
            
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


@with_progress_tracking("get_keyword_total_market_size", "Analyzing market size for keywords")
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
    update_node_progress(20.0, f"Fetching revenue data for {len(all_app_ids)} apps")
    
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


@with_progress_tracking("filter_keywords_by_market_size", "Filtering keywords by market size threshold")
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
    update_node_progress(50.0, f"Filtering {len(revenue_by_keyword)} keywords by ${threshold:,} threshold")
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


@with_progress_tracking("analyze_keyword_difficulty", "Analyzing keyword difficulty using ASO Mobile metrics")
async def analyze_keyword_difficulty(state: dict) -> dict:
    """
    LangGraph node to analyze keyword difficulty using ASO Mobile metrics via microservice.
    
    This node:
    1. Gets filtered keywords from state
    2. Checks database for already analyzed keywords
    3. Fetches real difficulty and traffic data from ASO Mobile using microservice for unanalyzed keywords
    4. Stores results in database
    5. Returns difficulty and traffic scores by keyword
    """
    from lib.aso_service_client import analyze_keywords_via_service
    
    filtered_keywords = state.get("filtered_keywords", [])
    if not filtered_keywords:
        print("No keywords to analyze for difficulty")
        return {
            "difficulty_by_keyword": {},
            "traffic_by_keyword": {}
        }
    
    # Get store instance
    store = get_aso_store()
    
    # Check which keywords already have cached metrics
    print(f"🔍 Checking database for cached keyword metrics...")
    update_node_progress(10.0, f"Checking cache for {len(filtered_keywords)} keywords")
    unanalyzed_keywords = await store.get_unanalyzed_keywords(filtered_keywords)
    
    difficulty_by_keyword = {}
    traffic_by_keyword = {}
    
    # Load cached metrics for already analyzed keywords
    cached_count = 0
    cached_weak_count = 0
    for keyword in filtered_keywords:
        if keyword not in unanalyzed_keywords:
            metrics = await store.get_keyword_metrics(keyword)
            if metrics:
                if metrics.get("difficulty", 0.0) == 0.0:
                    cached_weak_count += 1
                else:
                    difficulty_by_keyword[keyword] = metrics["difficulty"]
                    traffic_by_keyword[keyword] = metrics["traffic"]
                    cached_count += 1
    
    print(f"📊 Keyword Analysis Status:")
    print(f"  • Total keywords: {len(filtered_keywords)}")
    print(f"  • Already analyzed (cached): {cached_count}")
    print(f"  • Previously identified as weak: {cached_weak_count}")
    print(f"  • Needs analysis: {len(unanalyzed_keywords)}")
    
    # Only analyze unanalyzed keywords
    if unanalyzed_keywords:
        print(f"🔍 Fetching ASO metrics for {len(unanalyzed_keywords)} new keywords using microservice...")
        update_node_progress(40.0, f"Fetching ASO metrics for {len(unanalyzed_keywords)} keywords")
        
        failed_keywords = []
        
        try:
            # Call the microservice for unanalyzed keywords only
            correlation_id = state.get("correlation_id", None)
            keyword_metrics = await analyze_keywords_via_service(unanalyzed_keywords, correlation_id)
            
            if not keyword_metrics:
                print("⚠️ No metrics returned from ASO service")
            else:
                # Process the returned metrics
                weak_keywords = []
                for keyword in unanalyzed_keywords:
                    if keyword in keyword_metrics:
                        metrics = keyword_metrics[keyword]

                        # Check if keyword is weak (0.0 difficulty)
                        if metrics.difficulty == 0.0:
                            weak_keywords.append(keyword)
                            print(f"  '{keyword}': Too weak (difficulty: 0.0) - eliminated from analysis")
                        else:
                            difficulty_by_keyword[keyword] = metrics.difficulty
                            traffic_by_keyword[keyword] = metrics.traffic
                            
                            # Log detailed results
                            difficulty_level = "Easy" if metrics.difficulty <= 30 else "Medium" if metrics.difficulty <= 60 else "Hard" if metrics.difficulty <= 80 else "Very Hard"
                            traffic_level = "Low" if metrics.traffic <= 30 else "Medium" if metrics.traffic <= 60 else "High" if metrics.traffic <= 80 else "Very High"
                            
                            print(f"  '{keyword}':")
                            print(f"    Difficulty: {metrics.difficulty}/100 ({difficulty_level})")
                            print(f"    Traffic: {metrics.traffic}/100 ({traffic_level})")
                        
                        # Store in database (including weak keywords for future filtering)
                        await store.set_keyword_metrics(keyword, metrics.difficulty, metrics.traffic)
                    else:
                        failed_keywords.append(keyword)
                        print(f"⚠️ No metrics found for keyword '{keyword}'")
                        
        except Exception as e:
            print(f"❌ Error fetching ASO metrics: {e}")
            raise e
    
    # Calculate statistics
    total_weak_keywords = cached_weak_count + (len(weak_keywords) if 'weak_keywords' in locals() else 0)
    
    if difficulty_by_keyword:
        avg_difficulty = sum(difficulty_by_keyword.values()) / len(difficulty_by_keyword)
        easy_keywords = len([k for k, v in difficulty_by_keyword.items() if v <= 30])
        medium_keywords = len([k for k, v in difficulty_by_keyword.items() if 30 < v <= 60])
        hard_keywords = len([k for k, v in difficulty_by_keyword.items() if v > 60])
        
        print(f"\n🎯 Keyword Difficulty Summary:")
        print(f"  • Average difficulty: {avg_difficulty:.2f}/100")
        print(f"  • Easy keywords (≤30): {easy_keywords}")
        print(f"  • Medium keywords (30-60): {medium_keywords}")
        print(f"  • Hard keywords (>60): {hard_keywords}")
        print(f"  • Weak keywords (eliminated): {total_weak_keywords}")
        
        if unanalyzed_keywords and failed_keywords:
            print(f"  • Failed analyses: {len(failed_keywords)}")
        
        # Traffic statistics
        if traffic_by_keyword:
            avg_traffic = sum(traffic_by_keyword.values()) / len(traffic_by_keyword)
            print(f"\n📊 Keyword Traffic Summary:")
            print(f"  • Average traffic: {avg_traffic:.2f}/100")
    elif total_weak_keywords > 0:
        print(f"\n🎯 Keyword Analysis Summary:")
        print(f"  • All {total_weak_keywords} keywords were too weak (difficulty: 0.0) and eliminated")
    
    return {
        "difficulty_by_keyword": difficulty_by_keyword,
        "traffic_by_keyword": traffic_by_keyword
    }


@with_progress_tracking("generate_final_report", "Generating comprehensive ASO analysis report")
async def generate_final_report(state: dict) -> dict:
    """
    Generate comprehensive ASO analysis report with computed analysis for direct display.
    
    This now includes all the analysis logic previously done in the Streamlit client,
    making the client a thin presentation layer.
    """
    ideas = state.get("ideas", [])
    revenue_by_keyword = state.get("revenue_by_keyword", {})
    difficulty_by_keyword = state.get("difficulty_by_keyword", {})
    traffic_by_keyword = state.get("traffic_by_keyword", {})
    initial_keywords = state.get("initial_keywords", {})
    
    print(f"\n📊 Generating Final ASO Analysis Report with Computed Analysis...")
    update_node_progress(20.0, f"Generating structured report for {len(ideas)} app ideas")
    
    # Helper function to calculate opportunity score
    def calculate_opportunity_score(keyword_data):
        difficulty = keyword_data.get('difficulty_rating', 1)
        traffic = keyword_data.get('traffic_rating', 0)
        if difficulty == 0:
            return 0.0
        return round((traffic / difficulty) * 10, 2)
    
    # Helper function to categorize keywords
    def categorize_keyword(keyword_data, market_threshold=50000):
        difficulty = keyword_data.get('difficulty_rating', 0)
        traffic = keyword_data.get('traffic_rating', 0)
        market_size = keyword_data.get('market_size_usd', 0)
        
        if difficulty == 0.0:
            return "weak"
        elif market_size >= market_threshold and traffic >= 200 and difficulty < 3.0:
            return "top_performer"
        elif market_size >= market_threshold and traffic >= 100 and difficulty < 4.0:
            return "good"
        elif market_size < market_threshold:
            return "low_market"
        elif difficulty >= 4.0:
            return "too_difficult"
        elif traffic < 100:
            return "low_traffic"
        else:
            return "low_potential"
    
    # Generate structured report for each app idea
    app_analysis = {}
    
    for idea in ideas:
        # Get keywords related to this idea
        idea_keywords = initial_keywords.get(idea, [])
        
        if not idea_keywords:
            app_analysis[idea] = {
                "best_possible_market_size_usd": 0,
                "keywords": {},
                "summary": {
                    "total_keywords": 0,
                    "viable_keywords": 0,
                    "top_performers": [],
                    "avg_difficulty": 0.0,
                    "avg_traffic": 0.0,
                    "best_difficulty": 0.0,
                    "best_traffic": 0.0,
                    "opportunity_score": 0.0
                }
            }
            continue
        
        # Calculate best possible market size (maximum value of all keywords for this idea)
        keyword_market_sizes = [
            revenue_by_keyword.get(keyword, 0) 
            for keyword in idea_keywords
        ]
        best_possible_market_size = max(keyword_market_sizes) if keyword_market_sizes else 0
        
        # Build keyword dictionary with all metrics and computed analysis
        keywords_data = {}
        viable_keywords = []
        top_performers = []
        
        for keyword in idea_keywords:
            market_size = revenue_by_keyword.get(keyword, 0)
            difficulty_score = difficulty_by_keyword.get(keyword, 0.0)
            traffic_score = traffic_by_keyword.get(keyword, 0.0)
            
            keyword_data = {
                "difficulty_rating": round(difficulty_score, 2),
                "traffic_rating": traffic_score,
                "market_size_usd": market_size,
                "opportunity_score": 0.0,
                "category": "weak"
            }
            
            # Calculate opportunity score
            keyword_data["opportunity_score"] = calculate_opportunity_score(keyword_data)
            
            # Categorize keyword
            category = categorize_keyword(keyword_data)
            keyword_data["category"] = category
            
            # Add to top performers if applicable
            if category == "top_performer":
                top_performers.append({
                    'keyword': keyword,
                    'difficulty': difficulty_score,
                    'traffic': traffic_score,
                    'market_size': market_size,
                    'opportunity_score': keyword_data["opportunity_score"]
                })
            
            keywords_data[keyword] = keyword_data
            
            # Track viable keywords (non-weak)
            if difficulty_score > 0.0:
                viable_keywords.append(keyword_data)
        
        # Sort top performers by opportunity score
        top_performers.sort(key=lambda x: x['opportunity_score'], reverse=True)
        
        # Calculate summary statistics
        if viable_keywords:
            difficulties = [k['difficulty_rating'] for k in viable_keywords]
            traffics = [k['traffic_rating'] for k in viable_keywords]
            
            avg_difficulty = round(sum(difficulties) / len(difficulties), 1)
            avg_traffic = round(sum(traffics) / len(traffics), 1)
            best_difficulty = round(min(difficulties), 1)
            best_traffic = round(max(traffics), 1)
            
            # Calculate overall opportunity score
            opportunity_scores = [k['opportunity_score'] for k in viable_keywords]
            avg_opportunity = round(sum(opportunity_scores) / len(opportunity_scores), 2)
        else:
            avg_difficulty = avg_traffic = best_difficulty = best_traffic = avg_opportunity = 0.0
        
        app_analysis[idea] = {
            "best_possible_market_size_usd": best_possible_market_size,
            "keywords": keywords_data,
            "summary": {
                "total_keywords": len(idea_keywords),
                "viable_keywords": len(viable_keywords),
                "top_performers": top_performers[:3],  # Top 3 performers
                "avg_difficulty": avg_difficulty,
                "avg_traffic": avg_traffic,
                "best_difficulty": best_difficulty,
                "best_traffic": best_traffic,
                "opportunity_score": avg_opportunity
            }
        }
    
    # Calculate overall statistics
    total_keywords_analyzed = len(revenue_by_keyword)
    total_market_size = sum(revenue_by_keyword.values())
    difficulty_analyses_completed = len(difficulty_by_keyword)
    
    # Get store statistics
    store = get_aso_store()
    store_stats = await store.get_stats()
    
    # Structure final report for direct consumption
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
        "app_ideas": app_analysis,
        "display_ready": True  # Flag indicating this report is ready for direct display
    }
    
    # Print summary for monitoring
    print(f"✅ Comprehensive Analysis Report Generated!")
    print(f"  • App ideas analyzed: {len(ideas)}")
    print(f"  • Keywords evaluated: {total_keywords_analyzed}")
    print(f"  • Difficulty analyses: {difficulty_analyses_completed}")
    print(f"  • Total market opportunity: ${total_market_size:,.2f}")
    print(f"  • Store efficiency: {store_stats.get('active_items', 0)} active items across {store_stats.get('namespaces', 0)} namespaces")
    
    # Print structured data for each app idea
    for idea, analysis in app_analysis.items():
        summary = analysis['summary']
        
        print(f"\n🎯 {idea.title()}:")
        print(f"  • Best possible market size: ${analysis['best_possible_market_size_usd']:,.2f}")
        print(f"  • Total keywords: {summary['total_keywords']}")
        print(f"  • Viable keywords: {summary['viable_keywords']}")
        print(f"  • Top performers: {len(summary['top_performers'])}")
        
        if summary['top_performers']:
            print(f"  • Best opportunities:")
            for performer in summary['top_performers']:
                print(f"    - '{performer['keyword']}': ${performer['market_size']:,.0f} (difficulty: {performer['difficulty']:.1f}, opportunity: {performer['opportunity_score']:.1f})")
    
    return {"final_report": final_report}


test_graph = (
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