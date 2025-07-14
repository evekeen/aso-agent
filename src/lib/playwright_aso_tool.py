"""Direct Playwright automation for ASO Mobile tasks."""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, BrowserContext
from dotenv import load_dotenv

load_dotenv()


@dataclass
class KeywordMetrics:
    """Metrics for a keyword from ASO Mobile."""
    difficulty: float
    traffic: float


class PlaywrightASOTool:
    """Direct Playwright automation tool for ASO Mobile tasks."""
    
    def __init__(self):
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Load credentials from environment variables
        self.aso_email = os.getenv('ASO_EMAIL')
        self.aso_password = os.getenv('ASO_PASSWORD')
        self.aso_app_name = os.getenv('ASO_APP_NAME', 'Bedtime Fan')
        
        if not self.aso_email:
            raise ValueError("ASO_EMAIL environment variable is required")
        if not self.aso_password:
            raise ValueError("ASO_PASSWORD environment variable is required")
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_browser()
        
    async def start_browser(self):
        """Start browser with configured settings and persistent profile."""
        playwright = await async_playwright().start()
        
        # Create user data directory for persistent profile
        user_data_dir = Path('~/.config/playwright/aso-profile').expanduser()
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Launch browser with persistent context
        self.context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={'width': 1280, 'height': 1280},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security'
            ]
        )
        
        print("🔍 Opening new page...")
        
        self.page = await self.context.new_page()
        
    async def close_browser(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
            
    async def login_if_needed(self):
        """Login to ASO Mobile if not already logged in."""
        await self.page.goto("https://app.asomobile.net/monitor/list-view")
        print("🔍 Waiting for page to load...")
        await self.page.wait_for_load_state('domcontentloaded')
        
        print("🔍 Checking login status...")
        
        # Check if already logged in by looking for dashboard elements
        try:
            await self.page.wait_for_selector('app-toggle-menu-button', timeout=1000)
            print("✅ Already logged in")
            return True
        except:
            pass
            
        # Look for login form
        try:
            email_input = self.page.locator('input[type="email"]')
            if await email_input.is_visible():
                print("🔐 Logging in...")
                await email_input.fill(self.aso_email)
                
                password_input = self.page.locator('input[type="password"]')
                await password_input.fill(self.aso_password)
                
                login_button = self.page.locator('button[type="submit"]')
                await login_button.click()
                
                print("✅ Login completed")
                return True
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
            
    async def expand_left_menu(self):
        """Expand the left menu if collapsed."""
        await self.page.wait_for_selector('app-toggle-menu-button', timeout=10000)
        print("✅ Dashboard loaded")
                
        try:
            # Look for menu expansion button
            print("🔍 Checking left menu state...")
            menu_selector = 'app-toggle-menu-button > .collapse-menu'
            try:
                print("🔍 Waiting for menu toggle...")
                await self.page.wait_for_selector(menu_selector, timeout=1000)
            except Exception as e:
                if await self.page.locator('app-toggle-menu-button > .expand-menu').is_visible():
                    print("ℹ️ Left menu already expanded")
                    return True                
                else:
                    raise Exception("Left menu toggle not found")
            print("Getting the locator for the menu toggle...")
            menu_toggle = self.page.locator(menu_selector)
            print("🔍 Expanding left menu...")
            await menu_toggle.click()
            await self.page.wait_for_timeout(1000)
            print("✅ Expanded left menu")
            return True
        except Exception as e:
            print(f"❌ Failed to expand menu: {e}")
            return False
            
    async def select_app(self):
        """Select the specified app if not already selected."""
        try:
            # Check current app selection
            current_app = self.page.locator('.custom-main-app-select')
            if await current_app.is_visible():
                current_text = await current_app.text_content()
                if self.aso_app_name in current_text:
                    print(f"✅ App '{self.aso_app_name}' already selected")
                    return True
                    
            # Open app dropdown
            app_dropdown = self.page.locator('.custom-main-app-select .ng-value')
            await app_dropdown.dispatch_event('mousedown')
            await self.page.wait_for_timeout(1000)
            print("🔍 Selecting app from dropdown...")
            
            # Select the app
            app_option = self.page.get_by_text(self.aso_app_name, exact=False)
            await app_option.click()
            await self.page.wait_for_timeout(2000)
            
            print(f"✅ Selected app: {self.aso_app_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to select app: {e}")
            return False
            
    async def navigate_to_keyword_monitor(self):        
        await self.page.goto("https://app.asomobile.net/monitor/list-view")
        await self.page.wait_for_load_state('domcontentloaded')
        await self.page.wait_for_timeout(4000)
            
    async def delete_all_keywords(self):
        """Delete all existing keywords."""
        try:
            # Check if there are keywords to delete
            add_keywords_btn = self.page.get_by_text('Add keywords', exact=True)
            if await add_keywords_btn.is_visible():
                print("ℹ️ No keywords to delete")
                return True
            print("🔍 Deleting all existing keywords...")
                
            # Look for delete all button
            delete_all_btn = self.page.locator('button.aso-action-icon--trash').first
            await delete_all_btn.click()
            await self.page.wait_for_timeout(1000)
            
            # Confirm deletion
            confirm_btn = self.page.locator('button:text("Yes")')
            await confirm_btn.click()
            await self.page.wait_for_timeout(2000)
            
            print("✅ Deleted all keywords")
            return True            
                
        except Exception as e:
            print(f"❌ Failed to delete keywords: {e}")
            return False
            
    async def add_keywords(self, keywords: List[str]):
        """Add new keywords to monitor."""
        try:
            # Click add keywords button
            add_btn = self.page.get_by_text('Add keywords', exact=True)
            await add_btn.click()
            await self.page.wait_for_timeout(1000)
            
            # Enter keywords (comma-separated)
            keywords_input = self.page.locator('textarea').last
            keywords_text = ','.join(keywords)
            await keywords_input.fill(keywords_text)
            
            print(f"🔍 Adding {len(keywords)} keywords...")
            
            # Submit keywords
            submit_btn = self.page.locator('button:text("Add")').last
            await submit_btn.click()
            await self.page.wait_for_timeout(3000)
            
            print(f"✅ Added {len(keywords)} keywords")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add keywords: {e}")
            return False
            
    async def extract_keyword_metrics(self) -> Dict[str, KeywordMetrics]:
        """Extract keyword difficulty and traffic metrics from the page."""
        try:
            # Wait for keyword table to load
            await self.page.wait_for_selector('.keyword-table, table', timeout=10000)
            await self.page.wait_for_timeout(2000)
            
            keyword_metrics = {}
            
            # Find all keyword rows
            rows = self.page.locator('table tr, .keyword-row')
            row_count = await rows.count()
            
            for i in range(row_count):
                row = rows.nth(i)
                
                # Extract keyword name
                keyword_cell = row.locator('td:first-child, .keyword-name').first
                if not await keyword_cell.is_visible():
                    continue
                    
                keyword = await keyword_cell.text_content()
                if not keyword or keyword.strip() == '':
                    continue
                    
                # Extract difficulty
                difficulty_cell = row.locator('td:has-text("Difficulty"), .difficulty').first
                difficulty_text = await difficulty_cell.text_content() if await difficulty_cell.is_visible() else "0"
                difficulty = float(''.join(filter(str.isdigit, difficulty_text)) or 0)
                
                # Extract traffic/popularity
                traffic_cell = row.locator('td:has-text("Popularity"), td:has-text("Traffic"), .traffic, .popularity').first
                traffic_text = await traffic_cell.text_content() if await traffic_cell.is_visible() else "0"
                traffic = float(''.join(filter(str.isdigit, traffic_text)) or 0)
                
                keyword_metrics[keyword.strip()] = KeywordMetrics(
                    difficulty=difficulty,
                    traffic=traffic
                )
                
            print(f"✅ Extracted metrics for {len(keyword_metrics)} keywords")
            return keyword_metrics
            
        except Exception as e:
            print(f"❌ Failed to extract metrics: {e}")
            return {}
            
    async def download_keyword_metrics(self, keywords: List[str]) -> Dict[str, KeywordMetrics]:
        """Complete workflow to download keyword metrics."""
        try:
            # 1. Login if needed
            await self.login_if_needed()
            
            # 2. Expand menu
            await self.expand_left_menu()
            
            # 3. Select app
            await self.select_app()
            
            # 4. Navigate to keyword monitor
            await self.navigate_to_keyword_monitor()
            
            # 5. Delete existing keywords
            await self.delete_all_keywords()
            await self.delete_all_keywords()
            
            # 6. Add new keywords
            await self.add_keywords(keywords)
            
            # 7. Extract metrics
            return await self.extract_keyword_metrics()
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            return {}


# Convenience function
async def download_keyword_metrics_playwright(keywords: List[str]) -> Dict[str, KeywordMetrics]:
    """Download keyword metrics using direct Playwright automation."""
    async with PlaywrightASOTool() as tool:
        return await tool.download_keyword_metrics(keywords)


# Example usage
if __name__ == "__main__":
    async def test_playwright_tool():
        keywords = ["sleep sounds", "white noise", "bedtime stories", "lullabies", "meditation music"]
        
        result = await download_keyword_metrics_playwright(keywords)
        
        if result:
            print("✅ Successfully downloaded keyword metrics!")
            print(f"\nAnalyzed {len(result)} keywords:")
            for keyword, metrics in result.items():
                print(f"  - {keyword}: Difficulty={metrics.difficulty}, Traffic={metrics.traffic}")
        else:
            print("❌ No keyword metrics found!")
    
    asyncio.run(test_playwright_tool())