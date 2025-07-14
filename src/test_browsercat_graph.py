"""Test graph for BrowserCat + LangGraph integration debugging."""

import asyncio
import os
from dataclasses import dataclass
from typing import TypedDict
from langgraph.graph import MessagesState, StateGraph
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()


class Configuration(TypedDict):
    pass


@dataclass
class TestState(MessagesState):
    page_text: str = ""
    playwright_instance: object = None
    browser_instance: object = None


async def test_google_page(state: dict) -> dict:
    """Simple test node that opens Google and returns page text."""
    print("🔍 Starting test_google_page node...")
    
    # Get browser instances from state
    playwright_instance = state.get("playwright_instance")
    browser_instance = state.get("browser_instance")
    
    if not playwright_instance:
        raise ValueError("No playwright_instance provided in state")
    
    if not browser_instance:
        raise ValueError("No browser_instance provided in state")
    
    print("✅ Browser instances found in state")
    
    try:
        # Create a new context for this test
        print("🌐 Creating new browser context...")
        context = await browser_instance.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Create a new page
        print("📄 Creating new page...")
        page = await context.new_page()
        
        # Navigate to Google
        print("🚀 Navigating to Google...")
        await page.goto("https://www.google.com", wait_until="domcontentloaded")
        
        # Wait a moment for the page to fully load
        await page.wait_for_timeout(2000)
        
        # Get page title and some text
        title = await page.title()
        print(f"📑 Page title: {title}")
        
        # Try to get some text from the page
        try:
            # Look for the Google search input
            search_input = page.locator('textarea[name="q"]')
            if await search_input.is_visible():
                page_text = f"Successfully loaded Google.com - Title: {title}, Search input found"
            else:
                page_text = f"Loaded page with title: {title}, but search input not found"
        except Exception as e:
            page_text = f"Loaded page with title: {title}, error finding elements: {e}"
        
        print(f"✅ Page text extracted: {page_text}")
        
        # Close the context
        await context.close()
        print("🧹 Context closed")
        
        return {"page_text": page_text}
        
    except Exception as e:
        error_msg = f"❌ Error in test_google_page: {e}"
        print(error_msg)
        return {"page_text": error_msg}


# Create the test graph
test_graph = (
    StateGraph(TestState, config_schema=Configuration)
    .add_node("test_google_page", test_google_page)
    .add_edge("__start__", "test_google_page")
    .compile(name="BrowserCat Test Graph")
)


async def initialize_test_browser_resources():
    """Initialize Playwright and BrowserCat for testing."""
    print("🚀 Initializing test browser resources...")
    
    # Start Playwright
    playwright_instance = await async_playwright().start()
    print("✅ Playwright initialized")
    
    # Check if BrowserCat should be used
    browsercat_api_key = os.getenv('BROWSER_CAT_API_KEY')
    if not browsercat_api_key:
        raise ValueError("BROWSER_CAT_API_KEY environment variable is required")
    
    print("🌐 Connecting to BrowserCat...")
    browsercat_url = 'wss://api.browsercat.com/connect'
    browser_instance = await playwright_instance.chromium.connect(
        browsercat_url,
        headers={'Api-Key': browsercat_api_key}
    )
    print("✅ Connected to BrowserCat")
    
    return playwright_instance, browser_instance


async def cleanup_test_browser_resources(playwright_instance, browser_instance):
    """Cleanup test browser resources."""
    print("🧹 Cleaning up test browser resources...")
    
    if browser_instance:
        await browser_instance.close()
        print("✅ Browser closed")
    
    if playwright_instance:
        await playwright_instance.stop()
        print("✅ Playwright stopped")


async def run_test_graph():
    """Run the test graph with pre-initialized browser resources."""
    playwright_instance, browser_instance = await initialize_test_browser_resources()
    
    try:
        # Create initial state with browser instances
        initial_state = {
            "playwright_instance": playwright_instance,
            "browser_instance": browser_instance
        }
        
        print("🎯 Running test graph...")
        # Run the graph
        result = await test_graph.ainvoke(initial_state)
        
        print("🎉 Test graph completed!")
        print(f"📝 Result: {result.get('page_text', 'No page text found')}")
        
        return result
        
    finally:
        # Always cleanup resources
        await cleanup_test_browser_resources(playwright_instance, browser_instance)


if __name__ == "__main__":
    print("🧪 Starting BrowserCat + LangGraph integration test...")
    
    try:
        result = asyncio.run(run_test_graph())
        print(f"\n✅ Test completed successfully!")
        print(f"Final result: {result}")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()