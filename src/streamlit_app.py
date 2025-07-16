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
            max_value=50,
            value=20,
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
    
    # Main chat interface
    st.title(f"{APP_ICON} ASO Analysis Agent")
    st.markdown("**Analyze app ideas for App Store Optimization opportunities**")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message.type):
            st.write(message.content)
            
            # Display ASO-specific results
            if message.custom_data.get("final_report"):
                display_aso_results(message.custom_data["final_report"])
    
    # Chat input
    if user_input := st.chat_input("Describe your app ideas for ASO analysis..."):
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
            display_aso_results(final_report)
        
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
                display_aso_results(response.custom_data["final_report"])
                
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
                df = pd.DataFrame([
                    {"Keyword": k, "Market Size ($)": f"${v:,.2f}"}
                    for k, v in list(revenue_data.items())[:10]  # Show top 10
                ])
                st.dataframe(df, use_container_width=True)


def display_aso_results(final_report: Dict[str, Any]) -> None:
    """Display comprehensive ASO analysis results."""
    st.subheader("📊 ASO Analysis Results")
    
    app_ideas = final_report.get("app_ideas", {})
    if not app_ideas:
        st.warning("No analysis results available.")
        return
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "🎯 Keywords", "📊 Charts"])
    
    with tab1:
        display_overview_tab(app_ideas, final_report)
    
    with tab2:
        display_keywords_tab(app_ideas)
    
    with tab3:
        display_charts_tab(app_ideas)


def display_overview_tab(app_ideas: Dict[str, Any], final_report: Dict[str, Any]) -> None:
    """Display overview of all app ideas."""
    st.subheader("App Ideas Overview")
    
    # Summary metrics
    metadata = final_report.get("analysis_metadata", {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("App Ideas", len(app_ideas))
    with col2:
        st.metric("Keywords Analyzed", metadata.get("total_keywords_analyzed", 0))
    with col3:
        total_market = metadata.get("total_market_size_usd", 0)
        st.metric("Total Market Size", f"${total_market:,.0f}")
    with col4:
        st.metric("Difficulty Analyses", metadata.get("difficulty_analyses_completed", 0))
    
    # App ideas table
    overview_data = []
    for idea, analysis in app_ideas.items():
        keywords_data = analysis.get("keywords", {})
        overview_data.append({
            "App Idea": idea.title(),
            "Market Size ($)": f"${analysis.get('best_possible_market_size_usd', 0):,.2f}",
            "Keywords Analyzed": len(keywords_data),
            "Avg Difficulty": calculate_avg_difficulty(keywords_data),
            "Avg Traffic": calculate_avg_traffic(keywords_data),
            "Opportunity Score": calculate_opportunity_score_for_idea(keywords_data)
        })
    
    if overview_data:
        df = pd.DataFrame(overview_data)
        st.dataframe(df, use_container_width=True)


def display_keywords_tab(app_ideas: Dict[str, Any]) -> None:
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
        
        # Convert to DataFrame for better display
        keywords_data = []
        for keyword, data in keywords.items():
            keywords_data.append({
                "Keyword": keyword,
                "Difficulty": data.get('difficulty_rating', 0),
                "Traffic": data.get('traffic_rating', 0),
                "Market Size ($)": f"${data.get('market_size_usd', 0):,.2f}",
                "Opportunity Score": calculate_opportunity_score(data)
            })
        
        df = pd.DataFrame(keywords_data)
        
        # Sort by opportunity score
        df = df.sort_values("Opportunity Score", ascending=False)
        
        st.dataframe(df, use_container_width=True)
        
        # Export options
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Keywords CSV",
            data=csv,
            file_name=f"{selected_idea}_keywords_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


def display_charts_tab(app_ideas: Dict[str, Any]) -> None:
    """Display charts and visualizations."""
    st.subheader("Analysis Charts")
    
    # Prepare data for charts
    all_keywords = []
    for idea, analysis in app_ideas.items():
        keywords = analysis.get("keywords", {})
        for keyword, data in keywords.items():
            all_keywords.append({
                "App Idea": idea.title(),
                "Keyword": keyword,
                "Difficulty": data.get('difficulty_rating', 0),
                "Traffic": data.get('traffic_rating', 0),
                "Market Size": data.get('market_size_usd', 0)
            })
    
    if not all_keywords:
        st.warning("No keyword data available for charts.")
        return
    
    df = pd.DataFrame(all_keywords)
    
    # Market size by app idea
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Market Size by App Idea")
        market_by_idea = df.groupby("App Idea")["Market Size"].max().reset_index()
        fig1 = px.bar(
            market_by_idea,
            x="App Idea",
            y="Market Size",
            title="Best Market Opportunity per App Idea",
            labels={"Market Size": "Market Size ($)"}
        )
        fig1.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("Difficulty vs Traffic")
        fig2 = px.scatter(
            df,
            x="Difficulty",
            y="Traffic",
            size="Market Size",
            color="App Idea",
            hover_data=["Keyword"],
            title="Keyword Difficulty vs Traffic Analysis",
            labels={
                "Difficulty": "Difficulty Score (0-100)",
                "Traffic": "Traffic Score (0-100)"
            }
        )
        
        # Add quadrant lines
        fig2.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
        fig2.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Add quadrant labels
        fig2.add_annotation(x=25, y=75, text="High Traffic<br>Low Difficulty", showarrow=False, bgcolor="lightgreen", opacity=0.7)
        fig2.add_annotation(x=75, y=75, text="High Traffic<br>High Difficulty", showarrow=False, bgcolor="lightyellow", opacity=0.7)
        fig2.add_annotation(x=25, y=25, text="Low Traffic<br>Low Difficulty", showarrow=False, bgcolor="lightblue", opacity=0.7)
        fig2.add_annotation(x=75, y=25, text="Low Traffic<br>High Difficulty", showarrow=False, bgcolor="lightcoral", opacity=0.7)
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # Opportunity matrix
    st.subheader("Keyword Opportunity Matrix")
    
    # Calculate opportunity scores
    df["Opportunity Score"] = df.apply(
        lambda row: (row["Traffic"] / max(row["Difficulty"], 1)) * (row["Market Size"] / 1000), 
        axis=1
    )
    
    # Show top opportunities
    top_opportunities = df.nlargest(10, "Opportunity Score")
    
    fig3 = px.bar(
        top_opportunities,
        x="Keyword",
        y="Opportunity Score",
        color="App Idea",
        title="Top 10 Keyword Opportunities",
        hover_data=["Difficulty", "Traffic", "Market Size"]
    )
    fig3.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig3, use_container_width=True)


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