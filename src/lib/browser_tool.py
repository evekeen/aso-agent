"""Generic browser automation tool using browser-use for ASO tasks."""

import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from browser_use import Agent, Browser, BrowserConfig
from browser_use.llm import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BrowserTaskResult:
    """Result from browser automation task."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    screenshots: Optional[List[str]] = None


class ASOBrowserTool:
    """Generic browser automation tool for ASO-related tasks."""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        browser_binary_path: Optional[str] = None,
        chrome_profile_path: Optional[str] = None,
        headless: bool = False
    ):
        self.model = model
        self.api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Default browser paths for macOS
        self.browser_binary_path = browser_binary_path or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        self.chrome_profile_path = chrome_profile_path or str(
            Path.home() / 'Library' / 'Application Support' / 'Google' / 'Chrome' / 'Default'
        )
        self.headless = headless
    
    def _create_browser_config(self) -> BrowserConfig:
        """Create browser configuration."""
        return BrowserConfig(
            headless=self.headless
        )
    
    async def execute_task(self, task: str, timeout: int = 300) -> BrowserTaskResult:
        """
        Execute a browser automation task.
        
        Args:
            task: Detailed task description for the browser agent
            timeout: Maximum execution time in seconds
            
        Returns:
            BrowserTaskResult with success status and details
        """
        browser = Browser(config=self._create_browser_config())
        
        try:
            async with await browser.new_context() as ctx:
                agent = Agent(
                    task=task,
                    llm=ChatOpenAI(model=self.model, api_key=self.api_key),
                    browser=browser
                )
                
                # Execute with timeout
                result = await asyncio.wait_for(agent.run(), timeout=timeout)
                
                return BrowserTaskResult(
                    success=True,
                    message="Task completed successfully",
                    data={"result": str(result) if result else None}
                )
                
        except asyncio.TimeoutError:
            return BrowserTaskResult(
                success=False,
                message="Task timed out",
                error=f"Task exceeded {timeout} seconds timeout"
            )
        except Exception as e:
            return BrowserTaskResult(
                success=False,
                message="Task failed with error",
                error=str(e)
            )
        finally:
            try:
                await browser.close()
            except:
                pass  # Ignore cleanup errors


class ASOBrowserTasks:
    """Pre-defined ASO-specific browser automation tasks."""
    
    @staticmethod
    def add_app_to_aso_mobile(app_url: str, add_keywords: bool = True) -> str:
        """Generate task for adding app to ASO Mobile."""
        task = f"""
        Navigate to https://app.asomobile.net/monitor/list-view
        
        Steps to follow:
        1. Click on "Add New Application" button
        2. Enter the app URL: {app_url}
        3. {'Check the "Add suggested keywords" option' if add_keywords else 'Leave "Add suggested keywords" unchecked'}
        4. Click "Add App" button
        5. Wait for the app to be added successfully
        6. Confirm the app appears in the application list
        
        If there are any errors or login required, report them clearly.
        """
        return task
    
    @staticmethod
    def analyze_top_keywords(app_name: str) -> str:
        """Generate task for analyzing top keywords in ASO Mobile."""
        task = f"""
        Navigate to the ASO Mobile dashboard for the app: {app_name}
        
        Steps to follow:
        1. Find and click on the app named "{app_name}" in the application list
        2. Navigate to the "TOP" tab
        3. Extract the top 10 keywords with their rankings
        4. For each keyword, note:
           - Keyword text
           - Current ranking position
           - Difficulty score (if available)
           - Search volume (if available)
        5. Report the findings in a structured format
        
        If the app is not found or there are navigation issues, report them clearly.
        """
        return task
    
    @staticmethod
    def add_competitor_from_keywords(app_name: str, competitor_keywords: List[str]) -> str:
        """Generate task for adding competitors based on keywords."""
        keywords_list = ", ".join(competitor_keywords)
        task = f"""
        Navigate to the ASO Mobile dashboard for the app: {app_name}
        
        Steps to follow:
        1. Find and click on the app named "{app_name}" in the application list
        2. Navigate to the "TOP" tab
        3. Look for keywords: {keywords_list}
        4. For each keyword, find competing apps in the top rankings
        5. Add the top 3 competitors for each keyword to the competitor list
        6. Navigate to the competitors section and verify they were added
        7. Report which competitors were added and for which keywords
        
        If any steps fail or competitors cannot be added, report the issues clearly.
        """
        return task
    
    @staticmethod
    def extract_keyword_rankings(app_name: str, keywords: List[str]) -> str:
        """Generate task for extracting specific keyword rankings."""
        keywords_list = ", ".join(keywords)
        task = f"""
        Navigate to the ASO Mobile dashboard for the app: {app_name}
        
        Steps to follow:
        1. Find and click on the app named "{app_name}" in the application list
        2. Search for each of these keywords: {keywords_list}
        3. For each keyword, extract:           
           - Keyword difficulty
           - Estimated traffic
        4. Export the data in a structured format
        5. Report all findings clearly
        
        If any keywords are not found or data is unavailable, note this in the report.
        """
        return task
    
    @staticmethod
    def custom_aso_task(description: str, url: Optional[str] = None) -> str:
        """Generate a custom ASO-related browser task."""
        base_url = url or "https://app.asomobile.net"
        task = f"""
        Navigate to {base_url}
        
        Task Description: {description}
        
        General Guidelines:
        1. Follow the task description step by step
        2. Handle any login prompts or authentication if required
        3. Take screenshots of important steps or results
        4. Report any errors or unexpected behavior
        5. Provide detailed feedback on what was accomplished
        6. If the task cannot be completed, explain why and what was attempted
        
        Be thorough and accurate in reporting the results.
        """
        return task
    
    @staticmethod
    def get_difficulty_and_traffic_for_keywords(keywords: List[str]) -> str:
        return f"""
            ### Goal
            Extract keyword difficulty and traffic metrics from the ASO Mobile platform using automated navigation and AI-driven keyword suggestions.

            ---

            ### 📌 Execution Overview

            1. **Clean slate**: Delete all existing keywords from ASO Mobile
            2. **Keyword injection**: Add input keywords
            3. **AI enhancement**: Expand list using AI-suggested keywords
            4. **Data export**: Download XLSX report
            5. **Metric extraction**: Parse XLSX to extract difficulty and traffic values

            > 💡 Note: Ensure you're logged into ASO Mobile. This script assumes the "bedtimefan" app is available and credentials are auto-filled.

            ---

            ### 📂 Input - Comma-separated string or list of keyword terms
            {keywords}


            🔁 Step-by-Step Instructions

            1. Navigation
                •	Open ASO Mobile dashboard: https://app.asomobile.net/monitor/list-view

            2. Authentication
                •	It is assumed that you are already logged in
            3. App Selection
                •	Next button to the left of the "+ Application" button is the app selection dropdown
                •	Open the dropdown and select “Bedtime Fan: White nose baby” app

            4. Access Keyword Monitor
                - Navigate to "Keyword monitor" section in left sidebar
                - Click to access keyword monitoring interface

            5. Delete Existing Keywords
                - Click delete all "Trash" icon button in the keyword table header on the rightmost column
                - Click "Yes" button to confirm deletion

            6. Add Input Keywords
            - Click "➕ Add keywords" button (top-right corner)
            - Enter comma-separated keywords for current idea from Phase 1
            - Click "Add" button to confirm at the bottom right of the modal

            7. Export Keyword Report
                - Click "Download XLS file" button (top-right corner, 4th in a row with "➕ Add keywords")
                - XLSX report will be downloaded with keyword data in the Downloads folder
            """


# Convenience function for quick browser automation
async def automate_aso_task(
    task_description: str,
    model: str = "gpt-4o-mini",
    timeout: int = 300,
    headless: bool = False
) -> BrowserTaskResult:
    """
    Quick function to automate an ASO-related browser task.
    
    Args:
        task_description: Detailed description of what to do
        model: OpenAI model to use for the agent
        timeout: Maximum execution time in seconds
        headless: Whether to run browser in headless mode
        
    Returns:
        BrowserTaskResult with execution details
    """
    tool = ASOBrowserTool(model=model, headless=headless)
    return await tool.execute_task(task_description, timeout=timeout)


# Example usage for testing
if __name__ == "__main__":
    async def test_browser_tool():
        # Test getting difficulty and traffic for keywords
        task = ASOBrowserTasks.get_difficulty_and_traffic_for_keywords(
            "sleep sounds, white noise, bedtime stories, lullabies, meditation music"
        )
        
        result = await automate_aso_task(task)
        
        if result.success:
            print("✅ Task completed successfully!")
            print(f"Message: {result.message}")
            if result.data:
                print(f"Data: {result.data}")
        else:
            print("❌ Task failed!")
            print(f"Error: {result.error}")
    
    # Run the test
    asyncio.run(test_browser_tool())