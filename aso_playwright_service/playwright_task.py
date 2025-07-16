"""Playwright task execution for ASO Mobile automation."""

import asyncio
import os
from typing import Dict, List
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, BrowserContext, Browser
from dotenv import load_dotenv
from progress_reporter import get_progress_reporter, with_progress_tracking

goto_timeout = 45
action_timeout = 45
connect_timeout = 45
keyword_timeout = 45


@dataclass
class KeywordMetrics:
    """Metrics for a keyword from ASO Mobile."""
    difficulty: float
    traffic: float


class PlaywrightASOTask:
    """Task executor for ASO Mobile automation with fresh browser per task."""
    
    def __init__(self, correlation_id: str = None):
        load_dotenv()
        self.context = None
        self.page = None
        self.browser = None
        self.correlation_id = correlation_id
        self.progress_reporter = None
        
        # Load credentials
        self.aso_email = os.getenv('ASO_EMAIL')
        self.aso_password = os.getenv('ASO_PASSWORD')
        self.aso_app_name = os.getenv('ASO_APP_NAME', 'Bedtime Fan')
        self.browsercat_api_key = os.getenv('BROWSER_CAT_API_KEY')
        
        if not self.aso_email:
            raise ValueError("ASO_EMAIL environment variable is required")
        if not self.aso_password:
            raise ValueError("ASO_PASSWORD environment variable is required")
        if not self.browsercat_api_key:
            raise ValueError("BROWSER_CAT_API_KEY environment variable is required")
    
    @with_progress_tracking("browser_connection", "Connecting to BrowserCat")
    async def _connect_to_browsercat(self, playwright):
        """Connect to BrowserCat with timeout and retry."""
        print("🌐 Connecting to BrowserCat...")
        browsercat_url = 'wss://api.browsercat.com/connect'
        
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                print(f"🌐 Connection attempt {attempt + 1}/{max_retries + 1}...")
                
                self.browser = await asyncio.wait_for(
                    playwright.chromium.connect(
                        browsercat_url,
                        headers={'Api-Key': self.browsercat_api_key},
                        timeout=connect_timeout * 1000
                    ),
                    timeout=connect_timeout
                )
                print("🌐 Connected to BrowserCat")
                return
                
            except asyncio.TimeoutError:
                print(f"⏰ BrowserCat connection timeout after {connect_timeout}s")
                if attempt < max_retries:
                    print("🔄 Retrying connection...")
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"Failed to connect to BrowserCat after {max_retries + 1} attempts (timeout)")
                    
            except Exception as e:
                print(f"❌ BrowserCat connection failed: {e}")
                if attempt < max_retries:
                    print("🔄 Retrying connection...")
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"Failed to connect to BrowserCat after {max_retries + 1} attempts: {e}")
    
    @with_progress_tracking("page_creation", "Creating browser page")
    async def _create_page(self):
        """Create browser context and page."""
        print("🔍 Creating browser context...")
        
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 1280},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        print("🔍 Opening new page...")
        
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                print(f"🔍 Page creation attempt {attempt + 1}/{max_retries + 1}...")
                
                self.page = await asyncio.wait_for(
                    self.context.new_page(),
                    timeout=goto_timeout
                )
                print("✅ Page created successfully")
                return
                
            except asyncio.TimeoutError:
                print(f"⏰ Page creation timeout after {goto_timeout}s")
                if attempt < max_retries:
                    print("🔄 Retrying page creation...")
                    await asyncio.sleep(3)
                else:
                    raise Exception(f"Failed to create page after {max_retries + 1} attempts (timeout)")
                    
            except Exception as e:
                print(f"❌ Page creation failed: {e}")
                if attempt < max_retries:
                    print("🔄 Retrying page creation...")
                    await asyncio.sleep(3)
                else:
                    raise Exception(f"Failed to create page after {max_retries + 1} attempts: {e}")
    
    async def _navigate_with_retry(self, url: str, description: str):
        """Navigate to URL with timeout and retry."""
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                print(f"🔍 {description} attempt {attempt + 1}/{max_retries + 1}...")
                
                await asyncio.wait_for(
                    self.page.goto(url),
                    timeout=goto_timeout
                )
                print(f"✅ {description} successful")
                return
                
            except asyncio.TimeoutError:
                print(f"⏰ {description} timeout after {goto_timeout}s")
                if attempt < max_retries:
                    print(f"🔄 Retrying {description}...")
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"Failed {description} after {max_retries + 1} attempts (timeout)")
                    
            except Exception as e:
                print(f"❌ {description} failed: {e}")
                if attempt < max_retries:
                    print(f"🔄 Retrying {description}...")
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"Failed {description} after {max_retries + 1} attempts: {e}")
    
    @with_progress_tracking("login", "Logging into ASO Mobile")
    async def _login_if_needed(self):
        """Login to ASO Mobile if not already logged in."""
        await self._navigate_with_retry(
            "https://app.asomobile.net/monitor/list-view",
            "Login navigation"
        )
        
        print("🔍 Waiting for page to load...")
        await asyncio.wait_for(
            self.page.wait_for_load_state('domcontentloaded'),
            timeout=goto_timeout
        )
        
        print("🔍 Checking login status...")
        
        # Check if already logged in
        try:
            await self.page.wait_for_selector('app-toggle-menu-button', timeout=1000)
            print("✅ Already logged in")
            return True
        except:
            pass
            
        # Login if needed
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
    
    @with_progress_tracking("menu_setup", "Setting up navigation menu")
    async def _expand_left_menu(self):
        """Expand the left menu if collapsed."""
        await self.page.wait_for_selector('app-toggle-menu-button', timeout=action_timeout * 1000)
        print("✅ Dashboard loaded")
                
        try:
            print("🔍 Checking left menu state...")
            menu_selector = 'app-toggle-menu-button > .collapse-menu'
            try:
                await self.page.wait_for_selector(menu_selector, timeout=1000)
            except Exception as e:
                if await self.page.locator('app-toggle-menu-button > .expand-menu').is_visible():
                    print("ℹ️ Left menu already expanded")
                    return True                
                else:
                    raise Exception("Left menu toggle not found")
            
            menu_toggle = self.page.locator(menu_selector)
            print("🔍 Expanding left menu...")
            await menu_toggle.click()
            await self.page.wait_for_timeout(1000)
            print("✅ Expanded left menu")
            return True
        except Exception as e:
            print(f"❌ Failed to expand menu: {e}")
            return False
    
    @with_progress_tracking("app_selection", "Selecting target app")
    async def _select_app(self):
        """Select the specified app if not already selected."""
        try:
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
    
    @with_progress_tracking("navigation", "Navigating to keyword monitor")
    async def _navigate_to_keyword_monitor(self):
        """Navigate to keyword monitor page."""
        await self._navigate_with_retry(
            "https://app.asomobile.net/monitor/list-view",
            "Keyword monitor navigation"
        )
        
        await asyncio.wait_for(
            self.page.wait_for_load_state('domcontentloaded'),
            timeout=goto_timeout
        )
        await self.page.wait_for_timeout(2000)
    
    @with_progress_tracking("cleanup", "Cleaning up existing keywords")
    async def _delete_all_keywords(self):
        """Delete all existing keywords."""
        try:
            add_keywords_btn = self.page.get_by_text('Add keywords', exact=True)
            if await add_keywords_btn.is_visible():
                print("ℹ️ No keywords to delete")
                return True
            print("🔍 Deleting all existing keywords...")
                
            delete_all_btn = self.page.locator('button.aso-action-icon--trash').first
            await delete_all_btn.click()
            await self.page.wait_for_timeout(1000)
            
            confirm_btn = self.page.locator('button:text("Yes")')
            await confirm_btn.click()
            await self.page.wait_for_timeout(2000)
            
            print("✅ Deleted all keywords")
            return True            
                
        except Exception as e:
            print(f"❌ Failed to delete keywords: {e}")
            return False
    
    @with_progress_tracking("keyword_addition", "Adding keywords to monitor")
    async def _add_keywords(self, keywords: List[str]):
        """Add new keywords to monitor."""
        try:
            add_btn = self.page.get_by_text('Add keywords', exact=True)
            await add_btn.click()
            await self.page.wait_for_timeout(1000)
            
            keywords_input = self.page.locator('textarea').last
            keywords_text = ','.join(keywords)
            await keywords_input.fill(keywords_text)
            
            print(f"🔍 Adding {len(keywords)} keywords...")
            
            submit_btn = self.page.locator('button:text("Add")').last
            await submit_btn.click()
            await self.page.wait_for_timeout(3000)
            
            print(f"✅ Added {len(keywords)} keywords")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add keywords: {e}")
            return False
    
    @with_progress_tracking("metrics_extraction", "Extracting keyword metrics")
    async def _extract_keyword_metrics(self) -> Dict[str, KeywordMetrics]:
        """Extract keyword difficulty and traffic metrics from the page."""
        try:
            await self.page.wait_for_selector('table', timeout=keyword_timeout)
            paginator = self.page.locator('.p-paginator-rpp-options').first
            if not await paginator.is_visible():
                print("❌ Paginator not found, cannot extract metrics")
                return {}
            await paginator.click()            
            await self.page.wait_for_timeout(2000)
            
            option_200_selector = '.p-dropdown-items-wrapper .p-dropdown-item:has-text("200")'
            await self.page.wait_for_selector(option_200_selector, timeout=keyword_timeout)            
            option_200 = self.page.locator(option_200_selector)
            await option_200.click()            
            
            await self.page.wait_for_timeout(2000)
            
            print("🔍 Extracting keyword metrics...")
            
            keyword_metrics = {}
            
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
                
                keyword = await cells.nth(keyword_idx).text_content()
                if not keyword or keyword.strip() == '':
                    continue
                keyword = keyword.strip()
                
                difficulty_text = await cells.nth(complexity_idx).text_content()
                difficulty_text = difficulty_text.strip() if difficulty_text else "0"
                try:
                    difficulty = float(difficulty_text)
                except ValueError:
                    difficulty = float(''.join(c for c in difficulty_text if c.isdigit() or c == '.') or "0")
                
                traffic_text = await cells.nth(traffic_idx).text_content()
                traffic_text = traffic_text.strip() if traffic_text else "0"
                try:
                    traffic = float(traffic_text)
                except ValueError:
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
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def execute(self, keywords: List[str]) -> Dict[str, KeywordMetrics]:
        """Execute the complete keyword analysis workflow."""
        print(f"🔍 Starting ASO analysis for {len(keywords)} keywords...")
        
        # Initialize progress reporter if correlation ID is provided
        if self.correlation_id:
            self.progress_reporter = get_progress_reporter(self.correlation_id)
        
        try:
            if self.progress_reporter:
                async with self.progress_reporter:
                    return await self._execute_workflow(keywords)
            else:
                return await self._execute_workflow(keywords)
                
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            return {}
        finally:
            await self.cleanup()
    
    async def _execute_workflow(self, keywords: List[str]) -> Dict[str, KeywordMetrics]:
        """Execute the core workflow with clean business logic."""
        async with async_playwright() as playwright:
            # Connect to BrowserCat
            await self._connect_to_browsercat(playwright)
            
            # Create page
            await self._create_page()
            
            # Login
            await self._login_if_needed()
            
            # Expand menu
            await self._expand_left_menu()
            
            # Select app
            await self._select_app()
            
            # Navigate to keyword monitor
            await self._navigate_to_keyword_monitor()
            
            # Delete existing keywords
            await self._delete_all_keywords()
            await self._delete_all_keywords()  # Double cleanup for safety
            
            # Add new keywords
            await self._add_keywords(keywords)
            
            # Extract metrics
            metrics = await self._extract_keyword_metrics()
            
            # Report keyword processing results if progress reporter is available
            if self.progress_reporter:
                await self.progress_reporter.report_keywords_processed(metrics, len(keywords))
            
            return metrics


async def execute_keyword_analysis(keywords: List[str], correlation_id: str = None) -> Dict[str, KeywordMetrics]:
    """Execute keyword analysis task."""
    task = PlaywrightASOTask(correlation_id)
    return await task.execute(keywords)