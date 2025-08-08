import asyncio
import logging
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import os

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError(
        "Playwright not installed. Install with: pip install playwright && playwright install"
    )

logger = logging.getLogger(__name__)

@dataclass
class BrowserInstance:
    """
    Represents a single browser instance in our pool.
    Like having one kitchen oven that can be used by different chefs.
    """
    browser: Browser
    created_at: datetime
    last_used: datetime
    in_use: bool = False
    use_count: int = 0
    max_uses: int = 50  # Restart browser after 50 uses to prevent memory leaks

class BrowserManager:
    """
    Manages a pool of browser instances for efficient web automation.
    
    Think of this as the KITCHEN EQUIPMENT MANAGER who:
    - Keeps multiple ovens (browsers) ready for use
    - Assigns ovens to chefs (analyzers) when needed
    - Maintains and cleans ovens regularly
    - Replaces old ovens when they wear out
    
    Why do we need this?
    - Starting a browser is slow (3-5 seconds)
    - We want multiple analyses to run simultaneously
    - We need to prevent memory leaks from long-running browsers
    """
    
    def __init__(self, pool_size: int = 3, max_idle_time: int = 300):
        """
        Initialize the browser manager.
        
        Args:
            pool_size: Number of browsers to keep in the pool (like number of ovens)
            max_idle_time: Close browsers after this many seconds of inactivity
        """
        self.pool_size = pool_size
        self.max_idle_time = max_idle_time
        
        # Browser pool storage
        self._browser_pool: List[BrowserInstance] = []
        self._playwright = None
        self._initialized = False
        
        # Locks for thread safety
        self._pool_lock = asyncio.Lock()
        self._cleanup_task = None
        
        # Statistics
        self._total_browsers_created = 0
        self._total_pages_opened = 0
        
        logger.info(f"BrowserManager initialized with pool size: {pool_size}")
    
    async def initialize(self):
        """
        Initialize the browser manager and create initial browser pool.
        This is like warming up all the ovens before the restaurant opens.
        """
        if self._initialized:
            logger.warning("BrowserManager already initialized")
            return
        
        try:
            logger.info("Initializing BrowserManager...")
            
            # Start Playwright
            self._playwright = await async_playwright().start()
            
            # Create initial browser pool
            await self._create_initial_pool()
            
            # Start cleanup task (runs every 60 seconds to maintain browsers)
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self._initialized = True
            logger.info(f"BrowserManager initialized successfully with {len(self._browser_pool)} browsers")
            
        except Exception as e:
            logger.error(f"Failed to initialize BrowserManager: {e}")
            await self.cleanup()
            raise
    
    async def _create_initial_pool(self):
        """Create the initial pool of browsers"""
        for i in range(self.pool_size):
            try:
                browser_instance = await self._create_browser_instance()
                self._browser_pool.append(browser_instance)
                logger.info(f"Created browser {i+1}/{self.pool_size}")
            except Exception as e:
                logger.error(f"Failed to create browser {i+1}: {e}")
                # Continue with fewer browsers rather than failing completely
    
    async def _create_browser_instance(self) -> BrowserInstance:
        """
        Create a single browser instance with optimized settings.
        This is like buying and setting up a new oven.
        """
        if not self._playwright:
            raise RuntimeError("Playwright not initialized")
        
        # Browser launch options optimized for web analysis
        browser_options = {
            "headless": True,  # Run without GUI (faster)
            "args": [
                "--no-sandbox",  # Required for some servers
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",  # Overcome limited resource problems
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",  # Don't need GPU for analysis
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-web-security",  # Allow cross-origin requests for analysis
                "--disable-features=TranslateUI",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",  # Don't load images (faster analysis)
            ]
        }
        
        # Use different browser engines based on environment
        if os.getenv("PREFER_FIREFOX", "false").lower() == "true":
            browser = await self._playwright.firefox.launch(**browser_options)
        else:
            browser = await self._playwright.chromium.launch(**browser_options)
        
        self._total_browsers_created += 1
        
        return BrowserInstance(
            browser=browser,
            created_at=datetime.now(),
            last_used=datetime.now()
        )
    
    @asynccontextmanager
    async def get_browser_page(self, **page_options):
        """
        Get a browser page for analysis. This is the main method analyzers use.
        
        This is like borrowing an oven from the kitchen:
        1. Check out an available oven
        2. Use it for cooking
        3. Return it when done
        
        Usage:
            async with browser_manager.get_browser_page() as page:
                await page.goto("https://example.com")
                # Do analysis...
            # Page automatically cleaned up here
        """
        if not self._initialized:
            raise RuntimeError("BrowserManager not initialized. Call initialize() first.")
        
        browser_instance = None
        context = None
        page = None
        
        try:
            # Get an available browser from the pool
            browser_instance = await self._get_available_browser()
            
            # Create a new context (like a clean workspace)
            context_options = {
                "viewport": {"width": 1920, "height": 1080},  # Default desktop size
                "user_agent": "WebAudit-Pro/1.0 (Website Analysis Bot)",
                "ignore_https_errors": True,  # Ignore SSL errors for analysis
                **page_options
            }
            
            context = await browser_instance.browser.new_context(**context_options)
            
            # Create a new page
            page = await context.new_page()
            
            # Set reasonable timeouts
            page.set_default_timeout(30000)  # 30 seconds
            
            # Update usage statistics
            browser_instance.use_count += 1
            browser_instance.last_used = datetime.now()
            self._total_pages_opened += 1
            
            logger.debug(f"Provided browser page (uses: {browser_instance.use_count})")
            
            yield page
            
        except Exception as e:
            logger.error(f"Error providing browser page: {e}")
            raise
        finally:
            # Cleanup resources
            try:
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser_instance:
                    browser_instance.in_use = False
                    
                    # If browser has been used too much, mark it for replacement
                    if browser_instance.use_count >= browser_instance.max_uses:
                        await self._replace_browser_instance(browser_instance)
                        
            except Exception as e:
                logger.error(f"Error during browser page cleanup: {e}")
    
    async def _get_available_browser(self) -> BrowserInstance:
        """
        Get an available browser from the pool.
        If all are busy, wait for one to become available.
        """
        async with self._pool_lock:
            # First, try to find an available browser
            for browser_instance in self._browser_pool:
                if not browser_instance.in_use:
                    browser_instance.in_use = True
                    return browser_instance
            
            # If no browsers available, create a temporary one
            logger.warning("All browsers busy, creating temporary browser")
            temp_browser = await self._create_browser_instance()
            temp_browser.in_use = True
            return temp_browser
    
    async def _replace_browser_instance(self, old_instance: BrowserInstance):
        """
        Replace an old browser instance with a fresh one.
        This is like replacing an old oven that's getting worn out.
        """
        async with self._pool_lock:
            try:
                # Remove old browser from pool
                if old_instance in self._browser_pool:
                    self._browser_pool.remove(old_instance)
                
                # Close the old browser
                await old_instance.browser.close()
                
                # Create a new browser to replace it
                new_instance = await self._create_browser_instance()
                self._browser_pool.append(new_instance)
                
                logger.info(f"Replaced browser instance (old uses: {old_instance.use_count})")
                
            except Exception as e:
                logger.error(f"Error replacing browser instance: {e}")
    
    async def _cleanup_loop(self):
        """
        Background task that runs every minute to maintain the browser pool.
        This is like a janitor who cleans and maintains the kitchen equipment.
        """
        while self._initialized:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_idle_browsers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_idle_browsers(self):
        """Remove browsers that have been idle for too long"""
        if not self._initialized:
            return
        
        async with self._pool_lock:
            current_time = datetime.now()
            browsers_to_remove = []
            
            for browser_instance in self._browser_pool:
                # Check if browser has been idle too long
                idle_time = current_time - browser_instance.last_used
                
                if (not browser_instance.in_use and 
                    idle_time > timedelta(seconds=self.max_idle_time) and
                    len(self._browser_pool) > 1):  # Always keep at least 1 browser
                    
                    browsers_to_remove.append(browser_instance)
            
            # Remove idle browsers
            for browser_instance in browsers_to_remove:
                try:
                    self._browser_pool.remove(browser_instance)
                    await browser_instance.browser.close()
                    logger.info(f"Removed idle browser (idle for {idle_time.total_seconds():.0f}s)")
                except Exception as e:
                    logger.error(f"Error removing idle browser: {e}")
            
            # Ensure we have minimum number of browsers
            while len(self._browser_pool) < min(2, self.pool_size):
                try:
                    new_instance = await self._create_browser_instance()
                    self._browser_pool.append(new_instance)
                    logger.info("Created browser to maintain minimum pool size")
                except Exception as e:
                    logger.error(f"Error creating replacement browser: {e}")
                    break
    
    async def cleanup(self):
        """
        Clean up all resources when shutting down.
        This is like closing the kitchen and turning off all equipment.
        """
        logger.info("Starting BrowserManager cleanup...")
        
        self._initialized = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all browsers
        async with self._pool_lock:
            for browser_instance in self._browser_pool:
                try:
                    await browser_instance.browser.close()
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")
            
            self._browser_pool.clear()
        
        # Stop Playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}")
        
        logger.info("BrowserManager cleanup complete")
    
    def is_ready(self) -> bool:
        """Check if the browser manager is ready to handle requests"""
        return self._initialized and len(self._browser_pool) > 0
    
    def get_pool_size(self) -> int:
        """Get current number of browsers in pool"""
        return len(self._browser_pool)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get browser manager statistics"""
        active_browsers = sum(1 for b in self._browser_pool if b.in_use)
        
        return {
            "pool_size": len(self._browser_pool),
            "active_browsers": active_browsers,
            "available_browsers": len(self._browser_pool) - active_browsers,
            "total_browsers_created": self._total_browsers_created,
            "total_pages_opened": self._total_pages_opened,
            "is_ready": self.is_ready()
        }

# Helper functions for common browser configurations

async def create_mobile_page_options():
    """
    Get page options configured for mobile testing.
    This simulates an iPhone viewport.
    """
    return {
        "viewport": {"width": 375, "height": 667},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True
    }

async def create_desktop_page_options():
    """
    Get page options configured for desktop testing.
    This simulates a standard desktop browser.
    """
    return {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False
    }

# Example usage and testing functions
async def test_browser_manager():
    """
    Test function to verify the browser manager works correctly.
    This demonstrates how to use the browser manager.
    """
    manager = BrowserManager(pool_size=2)
    
    try:
        print("Initializing browser manager...")
        await manager.initialize()
        
        print(f"Browser manager ready: {manager.is_ready()}")
        print(f"Initial stats: {manager.get_stats()}")
        
        # Test getting a browser page
        print("\nTesting browser page...")
        async with manager.get_browser_page() as page:
            await page.goto("https://example.com")
            title = await page.title()
            print(f"Page title: {title}")
        
        # Test mobile page
        print("\nTesting mobile page...")
        mobile_options = await create_mobile_page_options()
        async with manager.get_browser_page(**mobile_options) as page:
            await page.goto("https://example.com")
            viewport = page.viewport_size
            print(f"Mobile viewport: {viewport}")
        
        print(f"\nFinal stats: {manager.get_stats()}")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        await manager.cleanup()
        print("Browser manager cleaned up")

if __name__ == "__main__":
    # Run test if this file is executed directly
    import asyncio
    asyncio.run(test_browser_manager())