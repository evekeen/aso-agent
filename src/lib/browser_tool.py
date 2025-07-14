"""Generic browser automation tool using browser-use for ASO tasks."""

import asyncio
import os
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
from pydantic import BaseModel
from playwright.async_api import Page
from browser_use import ActionResult, Agent, BrowserSession, Controller
from browser_use.llm import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


@dataclass
class KeywordMetrics:
    """Metrics for a keyword from ASO Mobile."""
    difficulty: float
    traffic: float


class KeywordMetricsOutput(BaseModel):
    """Structured output for keyword metrics."""
    difficulty: float
    traffic: float


class KeywordAnalysisResult(BaseModel):
    """Complete analysis result for all keywords."""
    keywords: Dict[str, KeywordMetricsOutput]
    
    class Config:
        extra = "forbid"
        

controller = Controller()
        
@controller.registry.action("click_delete_all_keywords")
def click_delete_all_keywords(page) -> ActionResult:
    """Click the delete all keywords button in the ASO Mobile interface."""
    page.locator('.aso-action-icon--trash').click()
    return ActionResult(success=True, message="Clicked delete all keywords button")


@controller.registry.action("expand_left_menu")
def expand_left_menu(page) -> ActionResult:
    """Expand the left menu in the ASO Mobile interface."""
    chevron = page.locator('app-toggle-menu-button > .expand-menu')
    if chevron.is_visible():
        chevron.click()
        return ActionResult(success=True, message="Expanded left menu")
    else:
        return ActionResult(success=False, message="Left menu already expanded or not found")

class ASOBrowserTool:
    """Generic browser automation tool for ASO-related tasks."""
    
    def __init__(
        self,
        model: str = "gpt-4.1-mini",
    ):
        self.model = model
        self.api_key = os.getenv('OPENAI_API_KEY')
        
        # Load ASO credentials from environment
        self.aso_email = os.getenv('ASO_EMAIL')
        self.aso_password = os.getenv('ASO_PASSWORD')
        self.aso_app_name = os.getenv('ASO_APP_NAME', 'Bedtime Fan: White noise baby')
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not self.aso_email:
            raise ValueError("ASO_EMAIL environment variable is required")
        if not self.aso_password:
            raise ValueError("ASO_PASSWORD environment variable is required")
                
    
    async def execute_task(self, task: str, timeout: int = 360000) -> Dict[str, KeywordMetrics]:
        """
        Execute a browser automation task.
        
        Args:
            task: Detailed task description for the browser agent
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary mapping keywords to their metrics
        """

        browser_session = BrowserSession(
            headless=False,
            viewport={'width': 2400, 'height': 1280},
            window_size={'width': 2400, 'height': 1280},
            user_data_dir=Path('~/.config/browseruse/profiles/aso').expanduser(),
            stealth=False,
            keep_alive=False,
            allowed_domains=['app.asomobile.net', 'asomobile.net'],
        )
        
        agent = Agent(
            task=task,
            llm=ChatOpenAI(model=self.model, api_key=self.api_key),
            browser_session=browser_session,
            controller=controller
        )
            
        try:
            history = await asyncio.wait_for(agent.run(), timeout=timeout)
            
            keyword_metrics = {}
            
            # Convert history to list if needed
            history_list = list(history) if hasattr(history, '__iter__') else []
            
            # Try to find the done action with extracted data
            for entry in history_list:
                if hasattr(entry, 'action') and entry.action:
                    action = entry.action
                    # Check if this is a done action with data
                    if hasattr(action, 'done') and action.done and hasattr(action, 'data'):
                        raw_data = action.data
                        if isinstance(raw_data, dict):
                            for keyword, metrics in raw_data.items():
                                if isinstance(metrics, dict) and 'difficulty' in metrics and 'traffic' in metrics:
                                    keyword_metrics[keyword] = KeywordMetrics(
                                        difficulty=float(metrics['difficulty']),
                                        traffic=float(metrics['traffic'])
                                    )
                            return keyword_metrics
            
            # If no done action found, try to extract from the last entry's result
            if history_list:
                last_entry = history_list[-1]
                if hasattr(last_entry, 'result'):
                    raw_data = last_entry.result
                    if isinstance(raw_data, dict):
                        for keyword, metrics in raw_data.items():
                            if isinstance(metrics, dict) and 'difficulty' in metrics and 'traffic' in metrics:
                                keyword_metrics[keyword] = KeywordMetrics(
                                    difficulty=float(metrics['difficulty']),
                                    traffic=float(metrics['traffic'])
                                )
                        return keyword_metrics
            
            return keyword_metrics
            
        except Exception as e:
            print(f"Error during browser automation: {e}")
            import traceback
            traceback.print_exc()
            return {}                                


# Convenience function for downloading keyword metrics
async def download_keyword_metrics(
    keywords: List[str],
    headless: bool = False
) -> Dict[str, KeywordMetrics]:
    """
    Download and parse keyword metrics from ASO Mobile.
    
    Args:
        keywords: List of keywords to analyze
        model: OpenAI model to use for the agent
        timeout: Maximum execution time in seconds
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary with keyword metrics (difficulty and traffic)
    """
    # Create tool instance to get credentials
    tool = ASOBrowserTool()
    
    task = f"""
            ### Goal
            Extract keyword difficulty and traffic(popularity) metrics from the ASO Mobile platform using automated navigation and AI-driven keyword suggestions.

            ---

            ### 📌 Execution Overview

            1. **Clean slate**: Delete all existing keywords from ASO Mobile
            2. **Keyword injection**: Add input keywords
            3. **Metric extraction**: Examine the page to extract difficulty and popularity values for each keyword

            > 💡 Note: Ensure you're logged into ASO Mobile. This script assumes the "bedtimefan" app is available and credentials are auto-filled.

            ---

            ### 📂 Input - Comma-separated string or list of keyword terms
            <keywords>
            {keywords}
            </keywords>


            🔁 Step-by-Step Instructions

            1. Navigation
                •	Open ASO Mobile dashboard: https://app.asomobile.net/monitor/list-view

            2. Authentication
                •	It is assumed that you are already logged in. If not, login with {tool.aso_email} {tool.aso_password}

            3. Menu state
                •	Expand the left menu in the ASO Mobile interface.
                •	It is very important to export the left menu before proceeding.
            4. App Selection        
                •	Check if the app from ASO_APP_NAME environment variable is not already selected. If it's selected skip to step 4. The selected app name is between "asomobile"  and the "+ Application" button in the top left corner of the page.
                •	Next button to the left of the "+ Application" button is the app selection dropdown
                •	Open the dropdown and select the app from ASO_APP_NAME environment variable

            5. Access Keyword Monitor
                - Navigate to "Keyword monitor" section in left sidebar
                - Click to access keyword monitoring interface

            6. Delete All Keywords
                - If there are no keywords, skip to step 6. The indicator ot that is the presence of the "+ Add keywords" button.
                - Click Delete all keywords button
                - Click "Yes" button to confirm deletion

            7. Add Input Keywords
                - Click "➕ Add keywords" button (top-right corner)
                - Enter comma-separated keywords for current idea
                - Click "Add" button to confirm at the bottom right of the modal

            8. Extract Keyword Report
                - Examine the keyword table at the bottom of the page
                - For each keyword, extract:
                    - **Difficulty**: Numeric value in the "Difficulty" column
                    - **Traffic**: Numeric value in the "Popularity" column (note: popularity is stored as traffic)
                - Return a JSON object in this exact format:
                  {{
                    "keywords": {{
                      "keyword1": {{"difficulty": 45.2, "traffic": 78.9}},
                      "keyword2": {{"difficulty": 23.1, "traffic": 56.7}},
                      ...
                    }}
                  }}
            """
    return await ASOBrowserTool().execute_task(task)


# Example usage for testing
if __name__ == "__main__":
    async def test_browser_tool():
        # Test downloading keyword metrics
        keywords = ["sleep sounds", "white noise", "bedtime stories", "lullabies", "meditation music"]
        
        result = await download_keyword_metrics(keywords, headless=False)
        
        if result:
            print("✅ Successfully downloaded keyword metrics!")
            print(f"\nAnalyzed {len(result)} keywords:")
            for keyword, metrics in result.items():
                print(f"  - {keyword}: Difficulty={metrics.difficulty}, Traffic={metrics.traffic}")
        else:
            print("❌ No keyword metrics found!")
    
    # Run the test
    asyncio.run(test_browser_tool())