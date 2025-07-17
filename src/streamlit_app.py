"""Streamlit frontend for ASO Agent Service."""

import streamlit as st
import asyncio
import uuid
import os
from typing import AsyncGenerator, Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.client.client import AgentClient, AgentClientError
from src.schema.schema import ChatMessage

APP_TITLE = "ASO Analysis Agent"
APP_ICON = "📱"


def get_or_create_user_id() -> str:
    """Get or create a unique user ID."""
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    return st.session_state.user_id


async def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        menu_items={},
    )
    
    # Initialize client
    user_id = get_or_create_user_id()
    
    if "agent_client" not in st.session_state:
        agent_url = os.getenv("AGENT_URL", "http://localhost:8080")
        try:
            with st.spinner("Connecting to ASO analysis service..."):
                st.session_state.agent_client = AgentClient(base_url=agent_url)
        except AgentClientError as e:
            st.error(f"Error connecting to service: {e}")
            st.stop()
    
    agent_client = st.session_state.agent_client
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model selection
        if agent_client.info and agent_client.info.models:
            model_options = agent_client.info.models
            default_idx = 0
            if agent_client.info.default_model in model_options:
                default_idx = model_options.index(agent_client.info.default_model)
        else:
            model_options = ["gpt-4o-mini"]
            default_idx = 0
            
        model = st.selectbox(
            "LLM Model",
            options=model_options,
            index=default_idx
        )
        
        # Analysis settings
        st.subheader("ASO Analysis Settings")
        market_threshold = st.number_input(
            "Market Size Threshold ($)",
            min_value=1000,
            max_value=1000000,
            value=50000,
            step=1000,
            help="Minimum market size to include keywords in difficulty analysis"
        )
        
        keywords_per_idea = st.slider(
            "Keywords per App Idea",
            min_value=5,
            max_value=100,
            value=30,
            help="Number of keywords to generate for each app idea"
        )
        
        use_streaming = st.toggle("Stream Results", value=True)
        
        # Clear conversation
        if st.button("🗑️ Clear Conversation"):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
        
        # Info section
        st.subheader("ℹ️ How to Use")
        st.markdown("""
        1. **Describe your app ideas** in the chat
        2. **Wait for analysis** to complete
        3. **Review results** including:
           - Market size opportunities
           - Keyword difficulty scores
           - Traffic potential
        4. **Export data** for further analysis
        """)
        
        st.subheader("💡 Example Prompts")
        st.markdown("""
        **Clear requests (will proceed directly):**
        - "Analyze fitness tracking apps"
        - "I want to explore meditation and sleep apps"
        - "Research productivity apps for students"
        - "Investigate cooking and recipe apps"
        
        **Vague requests (agent will ask for clarification):**
        - "I have an app idea"
        - "Apps for my business"
        - "Something with social features"
        - "Health apps"
        """)
    
    # Main chat interface
    st.title(f"{APP_ICON} ASO Analysis Agent")
    st.markdown("**Analyze app ideas for App Store Optimization opportunities**")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message.type):
            st.write(message.content)
            
            # Display ASO-specific results
            if message.custom_data.get("final_report"):
                display_aso_results(message.custom_data["final_report"], market_threshold)
    
    # Chat input
    if user_input := st.chat_input("Describe the app ideas you want to analyze (e.g., 'fitness tracking apps' or 'productivity tools for students')"):
        # Add user message
        user_message = ChatMessage(type="human", content=user_input)
        st.session_state.messages.append(user_message)
        
        with st.chat_message("human"):
            st.write(user_input)
        
        # Get agent response
        with st.chat_message("ai"):
            if use_streaming:
                await handle_streaming_response(
                    agent_client, user_input, model, 
                    market_threshold, keywords_per_idea
                )
            else:
                await handle_single_response(
                    agent_client, user_input, model,
                    market_threshold, keywords_per_idea
                )


async def handle_streaming_response(
    client: AgentClient, 
    message: str, 
    model: str, 
    market_threshold: int, 
    keywords_per_idea: int
) -> None:
    """Handle streaming response with progress updates."""
    
    # Create containers for different types of updates
    progress_container = st.empty()
    message_container = st.empty()
    results_container = st.empty()
    
    try:
        stream = client.astream(
            message=message,
            model=model,
            thread_id=st.session_state.thread_id,
            user_id=st.session_state.user_id,
            agent_config={
                "market_threshold": market_threshold,
                "keywords_per_idea": keywords_per_idea
            }
        )
        
        full_response = ""
        final_report = None
        
        async for event in stream:
            event_type = event.get("type")
            content = event.get("content", {})
            
            if event_type == "progress":
                # Update progress bar
                update_progress_display(progress_container, content)
                
            elif event_type == "message":
                # Update main message
                if isinstance(content, dict):
                    message_content = content.get("content", "")
                    custom_data = content.get("custom_data", {})
                else:
                    message_content = str(content)
                    custom_data = {}
                
                if message_content:
                    full_response += message_content
                    message_container.markdown(full_response)
                
                # Check for final report
                if custom_data.get("final_report"):
                    final_report = custom_data["final_report"]
                    
            elif event_type == "intermediate":
                # Show intermediate results
                display_intermediate_results(results_container, content)
                
            elif event_type == "interrupt":
                # Handle interrupt (agent asking for clarification)
                interrupt_message = content.get("message", "Agent is asking for clarification")
                st.info(f"💬 {interrupt_message}")
                # The conversation continues, user can respond in chat
                
            elif event_type == "error":
                st.error(f"Analysis error: {content}")
                return
        
        # Store final message
        ai_message = ChatMessage(
            type="ai",
            content=full_response,
            custom_data={"final_report": final_report} if final_report else {}
        )
        st.session_state.messages.append(ai_message)
        
        # Display final results
        if final_report:
            display_aso_results(final_report, market_threshold)
        
        # Clear progress display
        progress_container.empty()
            
    except Exception as e:
        st.error(f"Error during ASO analysis: {e}")


async def handle_single_response(
    client: AgentClient, 
    message: str, 
    model: str,
    market_threshold: int, 
    keywords_per_idea: int
) -> None:
    """Handle single (non-streaming) response."""
    
    with st.spinner("Running ASO analysis..."):
        try:
            response = await client.ainvoke(
                message=message,
                model=model,
                thread_id=st.session_state.thread_id,
                user_id=st.session_state.user_id,
                agent_config={
                    "market_threshold": market_threshold,
                    "keywords_per_idea": keywords_per_idea
                }
            )
            
            st.session_state.messages.append(response)
            st.write(response.content)
            
            # Display results if available
            if response.custom_data.get("final_report"):
                display_aso_results(response.custom_data["final_report"], market_threshold)
                
        except Exception as e:
            st.error(f"Error during ASO analysis: {e}")


def update_progress_display(container, progress_data: Dict[str, Any]) -> None:
    """Update progress display with current analysis step."""
    node_name = progress_data.get("node_name", "").replace("_", " ").title()
    progress_pct = progress_data.get("progress_percentage", 0)
    status_message = progress_data.get("status_message", "")
    
    with container.container():
        st.subheader(f"🔄 {node_name}")
        st.progress(min(progress_pct / 100, 1.0))
        if status_message:
            st.caption(status_message)


def display_intermediate_results(container, data: Dict[str, Any]) -> None:
    """Display intermediate results during analysis."""
    result_type = data.get("result_type")
    result_data = data.get("data", {})
    
    with container.container():
        if result_type == "keywords_found":
            st.subheader("📝 Keywords Generated")
            keywords_data = result_data.get("keywords", {})
            for idea, keywords in keywords_data.items():
                with st.expander(f"Keywords for {idea.title()}", expanded=True):
                    st.write(", ".join(keywords[:10]) + ("..." if len(keywords) > 10 else ""))
                
        elif result_type == "apps_found":
            st.subheader("📱 Apps Found")
            total_apps = result_data.get("total_apps", 0)
            st.metric("Total Apps Found", total_apps)
            
        elif result_type == "market_size_calculated":
            st.subheader("💰 Market Size Analysis")
            revenue_data = result_data.get("revenue_by_keyword", {})
            if revenue_data:
                # Sort by revenue descending and show top 10
                sorted_revenue = sorted(revenue_data.items(), key=lambda x: x[1], reverse=True)
                df = pd.DataFrame([
                    {"Keyword": k, "Market Size ($)": f"${v:,.2f}"}
                    for k, v in sorted_revenue[:10]  # Show top 10
                ])
                st.dataframe(df, use_container_width=True)


def display_aso_results(final_report: Dict[str, Any], market_threshold: int = 50000) -> None:
    """Display comprehensive ASO analysis results."""
    st.subheader("📊 ASO Analysis Results")
    
    app_ideas = final_report.get("app_ideas", {})
    if not app_ideas:
        st.warning("No analysis results available.")
        return
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["📈 Overview", "🎯 Keywords"])
    
    with tab1:
        display_overview_tab(app_ideas, final_report, market_threshold)
    
    with tab2:
        display_keywords_tab(app_ideas, market_threshold)


def display_overview_tab(app_ideas: Dict[str, Any], final_report: Dict[str, Any], market_threshold: int) -> None:
    """Display overview of all app ideas."""
    st.subheader("App Ideas Overview")
    
    # Summary metrics
    metadata = final_report.get("analysis_metadata", {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("App Ideas", len(app_ideas))
    with col2:
        st.metric("Keywords Analyzed", metadata.get("total_keywords_analyzed", 0))
    with col3:
        st.metric("Difficulty Analyses", metadata.get("difficulty_analyses_completed", 0))
    
    # App ideas with best performing keywords
    for idea, analysis in app_ideas.items():
        keywords_data = analysis.get("keywords", {})
        # Filter out weak keywords and find best performing ones
        viable_keywords = {k: v for k, v in keywords_data.items() if v.get('difficulty_rating', 0) > 0.0}
        
        # Find best performing keywords based on market threshold and difficulty
        best_keywords = []
        for keyword, data in viable_keywords.items():
            difficulty = data.get('difficulty_rating', 0)
            traffic = data.get('traffic_rating', 0)
            market_size = data.get('market_size_usd', 0)
            
            # Filter by criteria: market size meets threshold, good traffic, reasonable difficulty
            if market_size >= market_threshold and traffic >= 200 and difficulty < 3.0:
                best_keywords.append({
                    'keyword': keyword,
                    'difficulty': difficulty,
                    'traffic': traffic,
                    'market_size': market_size,
                    'opportunity_score': traffic / max(difficulty, 1)  # Higher is better
                })
        
        # Sort by opportunity score (traffic/difficulty ratio) descending
        best_keywords.sort(key=lambda x: x['opportunity_score'], reverse=True)
        
        # Display app idea section
        st.subheader(f"🎯 {idea.title()}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Best Market Size", f"${analysis.get('best_possible_market_size_usd', 0):,.0f}")
        with col2:
            st.metric("Total Keywords", len(keywords_data))
        with col3:
            st.metric("Viable Keywords", len(viable_keywords))
        
        # Show top 3 best performing keywords
        if best_keywords:
            st.write("**🏆 Top Performing Keywords:**")
            for i, kw in enumerate(best_keywords[:3], 1):
                with st.expander(f"#{i} {kw['keyword']}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Difficulty", f"{kw['difficulty']:.1f}/10")
                    with col2:
                        st.metric("Traffic", f"{kw['traffic']:.0f}/100")
                    with col3:
                        st.metric("Market Size", f"${kw['market_size']:,.0f}")
                    with col4:
                        st.metric("Opportunity Score", f"{kw['opportunity_score']:.1f}")
        else:
            st.warning(f"No keywords meet the criteria (Market Size ≥ ${market_threshold:,}, Traffic ≥ 200, Difficulty < 3.0)")
        
        st.divider()


def display_keywords_tab(app_ideas: Dict[str, Any], market_threshold: int) -> None:
    """Display detailed keyword analysis."""
    st.subheader("Keyword Analysis")
    
    # App idea selector
    idea_options = list(app_ideas.keys())
    if not idea_options:
        st.warning("No app ideas available.")
        return
        
    selected_idea = st.selectbox(
        "Select App Idea",
        options=idea_options,
        format_func=lambda x: x.title()
    )
    
    if selected_idea:
        keywords = app_ideas[selected_idea].get('keywords', {})
        
        if not keywords:
            st.warning(f"No keywords available for {selected_idea}")
            return
        
        # Convert to DataFrame for detailed analysis - show ALL keywords analyzed
        keywords_data = []
        for keyword, data in keywords.items():
            difficulty = data.get('difficulty_rating', 0)
            traffic = data.get('traffic_rating', 0)
            market_size = data.get('market_size_usd', 0)
            
            # Show status for each keyword based on market threshold and difficulty (0-10 scale)
            if difficulty == 0.0:
                status = "❌ Weak"
            elif market_size >= market_threshold and traffic >= 200 and difficulty < 3.0:
                status = "🏆 Top Performer"
            elif market_size >= market_threshold and traffic >= 100 and difficulty < 4.0:
                status = "✅ Good"
            elif market_size < market_threshold:
                status = "💸 Low Market"
            elif difficulty >= 4.0:
                status = "🔴 Too Difficult"
            elif traffic < 100:
                status = "📉 Low Traffic"
            else:
                status = "⚠️ Low Potential"
            
            keywords_data.append({
                "Keyword": keyword,
                "Status": status,
                "Difficulty": difficulty,
                "Traffic": traffic,
                "Market Size ($)": f"${market_size:,.2f}",
                "Market Size (Raw)": market_size,  # For sorting
                "Opportunity Score": calculate_opportunity_score(data) if difficulty > 0 else 0
            })
        
        if not keywords_data:
            st.warning(f"No keywords found for {selected_idea}")
            return
        
        df = pd.DataFrame(keywords_data)
        
        # Sort by traffic descending as primary, then by market size descending as secondary
        df = df.sort_values(["Traffic", "Market Size (Raw)"], ascending=[False, False])
        
        # Remove the raw market size column for display
        df = df.drop("Market Size (Raw)", axis=1)
        
        st.dataframe(df, use_container_width=True)
        
        # Export options
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Keywords CSV",
            data=csv,
            file_name=f"{selected_idea}_keywords_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key=f"download_csv_{selected_idea}"
        )



def calculate_avg_difficulty(keywords: Dict[str, Any]) -> float:
    """Calculate average difficulty score."""
    if not keywords:
        return 0.0
    difficulties = [data.get('difficulty_rating', 0) for data in keywords.values()]
    return round(sum(difficulties) / len(difficulties), 1)


def calculate_avg_traffic(keywords: Dict[str, Any]) -> float:
    """Calculate average traffic score."""
    if not keywords:
        return 0.0
    traffic_scores = [data.get('traffic_rating', 0) for data in keywords.values()]
    return round(sum(traffic_scores) / len(traffic_scores), 1)


def calculate_best_difficulty(keywords: Dict[str, Any]) -> float:
    """Calculate best (lowest) difficulty score."""
    if not keywords:
        return 0.0
    difficulties = [data.get('difficulty_rating', 0) for data in keywords.values()]
    return round(min(difficulties), 1)


def calculate_best_traffic(keywords: Dict[str, Any]) -> float:
    """Calculate best (highest) traffic score."""
    if not keywords:
        return 0.0
    traffic_scores = [data.get('traffic_rating', 0) for data in keywords.values()]
    return round(max(traffic_scores), 1)


def calculate_opportunity_score(keyword_data: Dict[str, Any]) -> float:
    """Calculate opportunity score based on traffic/difficulty ratio."""
    difficulty = keyword_data.get('difficulty_rating', 1)
    traffic = keyword_data.get('traffic_rating', 0)
    
    if difficulty == 0:
        return 0.0
    
    # Higher traffic, lower difficulty = better opportunity
    return round((traffic / difficulty) * 10, 2)


def calculate_opportunity_score_for_idea(keywords: Dict[str, Any]) -> float:
    """Calculate overall opportunity score for an app idea."""
    if not keywords:
        return 0.0
    
    scores = [calculate_opportunity_score(data) for data in keywords.values()]
    return round(sum(scores) / len(scores), 2)


if __name__ == "__main__":
    asyncio.run(main())