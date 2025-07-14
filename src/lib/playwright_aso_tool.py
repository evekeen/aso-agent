"""Direct Playwright automation for ASO Mobile tasks."""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, BrowserContext
from dotenv import load_dotenv


@dataclass
class KeywordMetrics:
    """Metrics for a keyword from ASO Mobile."""
    difficulty: float
    traffic: float


class PlaywrightASOTool:
    """Direct Playwright automation tool for ASO Mobile tasks."""
    
    def __init__(self, use_browsercat: bool = True):
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.use_browsercat = use_browsercat
        
        # Load credentials from environment variables
        self.aso_email = os.getenv('ASO_EMAIL')
        self.aso_password = os.getenv('ASO_PASSWORD')
        self.aso_app_name = os.getenv('ASO_APP_NAME', 'Bedtime Fan')
        self.browsercat_api_key = os.getenv('BROWSER_CAT_API_KEY')
        
        if not self.aso_email:
            raise ValueError("ASO_EMAIL environment variable is required")
        if not self.aso_password:
            raise ValueError("ASO_PASSWORD environment variable is required")
        if self.use_browsercat and not self.browsercat_api_key:
            raise ValueError("BROWSER_CAT_API_KEY environment variable is required when use_browsercat=True")
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_browser()
        
    async def start_browser(self, playwright_instance=None, browser_instance=None):
        """Start browser with configured settings and persistent profile."""
        print("🔍 Starting Playwright browser...")
        
        if playwright_instance:
            self.playwright = playwright_instance
            print("🔍 Using provided Playwright instance")
        else:
            self.playwright = await async_playwright().start()
            print("🔍 Playwright started")
        
        if browser_instance:
            self.browser = browser_instance
            print("🌐 Using provided browser instance")
            
            # Create context with viewport settings
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 1280},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        elif self.use_browsercat:
            # Connect to BrowserCat
            print("🌐 Connecting to BrowserCat...")
            browsercat_url = 'wss://api.browsercat.com/connect'
            self.browser = await self.playwright.chromium.connect(
                browsercat_url,
                headers={'Api-Key': self.browsercat_api_key}
            )
            print("🌐 Connected to BrowserCat")
            
            # Create context with viewport settings
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 1280},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        else:
            # Use local browser with persistent profile
            print("🖥️ Starting local browser...")
            user_data_dir = Path('~/.config/playwright/aso-profile').expanduser()
            user_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Launch browser with persistent context
            self.context = await self.playwright.chromium.launch_persistent_context(
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
        
    async def close_browser(self, close_shared_resources=False):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        
        # Only close browser and playwright if they're not shared instances
        # or if explicitly requested
        if close_shared_resources:
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
            
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
            app_option = self.page.locator(f'.app-name.option:has-text("{self.aso_app_name}")')
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
            await self.page.wait_for_selector('table', timeout=10000)
            paginator = self.page.locator('.p-paginator-rpp-options').first
            if not await paginator.is_visible():
                print("❌ Paginator not found, cannot extract metrics")
                return {}
            await paginator.click()            
            await self.page.wait_for_timeout(1000)
            option_200 = self.page.locator('.p-dropdown-items-wrapper .p-dropdown-item:has-text("200")')
            await option_200.click()            
            
            await self.page.wait_for_timeout(2000)
            
            print("🔍 Extracting keyword metrics...")
            
            keyword_metrics = {}
            
            # Find all table rows
            rows = self.page.locator('table tr')
            row_count = await rows.count()
            
            if row_count < 2:
                print("❌ No data rows found in table")
                return keyword_metrics
            
            # Read header row to find column indices
            header_row = rows.nth(0)
            header_cells = header_row.locator('th, td')
            header_count = await header_cells.count()
            
            keyword_idx = -1
            complexity_idx = -1
            traffic_idx = -1
            
            print("🔍 Reading header row...")
            for j in range(header_count):
                header_text = await header_cells.nth(j).text_content()
                header_text = header_text.strip().lower() if header_text else ""
                
                if 'keyword' in header_text:
                    keyword_idx = j
                elif 'complexity' in header_text or 'difficulty' in header_text:
                    complexity_idx = j
                elif 'traffic' in header_text or 'popularity' in header_text:
                    traffic_idx = j
            
            print(f"Column indices - Keyword: {keyword_idx}, Complexity: {complexity_idx}, Traffic: {traffic_idx}")
            
            if keyword_idx == -1 or complexity_idx == -1 or traffic_idx == -1:
                print("❌ Could not find required columns in header")
                return keyword_metrics
            
            # Process data rows (skip header at index 0)
            print(f"Found {row_count - 1} data rows")
            
            for i in range(1, row_count):
                row = rows.nth(i)
                cells = row.locator('td')
                cell_count = await cells.count()
                
                if cell_count <= max(keyword_idx, complexity_idx, traffic_idx):
                    continue
                
                # Extract keyword name
                keyword = await cells.nth(keyword_idx).text_content()
                if not keyword or keyword.strip() == '':
                    continue
                keyword = keyword.strip()
                
                # Extract difficulty/complexity
                difficulty_text = await cells.nth(complexity_idx).text_content()
                difficulty_text = difficulty_text.strip() if difficulty_text else "0"
                # Handle float values like "45.2" or "100.0"
                try:
                    difficulty = float(difficulty_text)
                except ValueError:
                    # Fallback: extract numeric part if direct conversion fails
                    difficulty = float(''.join(c for c in difficulty_text if c.isdigit() or c == '.') or "0")
                
                # Extract traffic/popularity
                traffic_text = await cells.nth(traffic_idx).text_content()
                traffic_text = traffic_text.strip() if traffic_text else "0"
                # Handle float values
                try:
                    traffic = float(traffic_text)
                except ValueError:
                    # Fallback: extract numeric part if direct conversion fails
                    traffic = float(''.join(c for c in traffic_text if c.isdigit() or c == '.') or "0")
                
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
async def download_keyword_metrics_playwright(
    keywords: List[str], 
    use_browsercat: bool = True,
    playwright_instance=None,
    browser_instance=None
) -> Dict[str, KeywordMetrics]:
    """Download keyword metrics using direct Playwright automation."""
    tool = PlaywrightASOTool(use_browsercat=use_browsercat)
    
    try:
        await tool.start_browser(playwright_instance, browser_instance)
        return await tool.download_keyword_metrics(keywords)
    finally:
        # Don't close shared resources
        await tool.close_browser(close_shared_resources=False)


# Example usage
if __name__ == "__main__":
    load_dotenv()
    
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