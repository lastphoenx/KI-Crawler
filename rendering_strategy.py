"""HTML rendering strategies with optional JavaScript support."""

import logging
from abc import ABC, abstractmethod
from typing import Optional
import asyncio

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class RenderingStrategy(ABC):
    """Abstract base class for HTML rendering."""
    
    @abstractmethod
    async def render(self, url: str) -> Optional[str]:
        """Render URL and return HTML."""
        pass
    
    async def cleanup(self):
        """Cleanup resources (e.g., close browser)."""
        pass


class StaticRenderingStrategy(RenderingStrategy):
    """Default: Static HTML without JavaScript rendering."""
    
    async def render(self, url: str) -> Optional[str]:
        """Fetch HTML via requests (no JS)."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None


class PlaywrightRenderingStrategy(RenderingStrategy):
    """JavaScript rendering using Playwright."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize Playwright strategy.
        
        Args:
            headless: Run browser headless
            timeout: Navigation timeout in ms
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not installed. Install with:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )
        
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.playwright = None
    
    async def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-dev-shm-usage']
            )
            logger.info("✓ Browser launched (Playwright)")
    
    async def render(self, url: str, extract_css: bool = False, css_output_dir=None) -> Optional[str]:
        """Render URL with full JavaScript execution and optionally extract CSS."""
        try:
            await self._ensure_browser()
            
            page = await self.browser.new_page()
            page.set_default_timeout(self.timeout)
            
            try:
                await page.goto(url, wait_until='load', timeout=self.timeout)
                
                await page.wait_for_timeout(2000)
                
                try:
                    await page.wait_for_selector('main, [role="main"], .content, article', timeout=5000)
                except:
                    pass
                
                # Extract CSS if requested
                if extract_css and css_output_dir:
                    await self._extract_css_from_page(page, url, css_output_dir)
                
                html = await page.content()
                logger.debug(f"Rendered with JS: {url}")
                return html
            finally:
                await page.close()
        
        except Exception as e:
            logger.warning(f"Playwright rendering failed for {url}: {e}")
            return None
    
    async def _extract_css_from_page(self, page, url: str, output_dir):
        """Extract CSS content directly from loaded page"""
        from pathlib import Path
        from urllib.parse import urlparse
        
        try:
            # Get all stylesheets loaded in the page
            stylesheets = await page.evaluate('''() => {
                const sheets = [];
                for (const sheet of document.styleSheets) {
                    try {
                        if (sheet.href) {
                            // External stylesheet
                            const rules = Array.from(sheet.cssRules || [])
                                .map(rule => rule.cssText)
                                .join('\\n');
                            sheets.push({ href: sheet.href, content: rules });
                        }
                    } catch (e) {
                        // Cross-origin stylesheet - try fetching
                        if (sheet.href) {
                            sheets.push({ href: sheet.href, content: null });
                        }
                    }
                }
                
                // ✅ Extract inline <style> tags from rendered DOM
                const inlineStyles = Array.from(document.querySelectorAll('style'))
                    .map(s => s.textContent || '')
                    .filter(s => s.trim())
                    .join('\\n\\n');
                
                if (inlineStyles) {
                    sheets.push({ href: 'inline_rendered', content: inlineStyles });
                }
                
                return sheets;
            }''')
            
            # Save CSS files
            for sheet in stylesheets:
                if not sheet['href']:
                    continue
                    
                css_url = sheet['href']
                
                # Handle inline styles separately
                if css_url == 'inline_rendered':
                    filename = 'inline_rendered.css'
                else:
                    # Generate filename from URL
                    parsed = urlparse(css_url)
                    filename = Path(parsed.path).name
                    
                    if not filename or not filename.endswith('.css'):
                        filename = f"style_{hash(css_url) % 10000}.css"
                
                output_path = Path(output_dir) / filename
                
                # If we have content directly, use it
                if sheet['content']:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(sheet['content'])
                    
                    if css_url == 'inline_rendered':
                        logger.info(f"💾 Extracted inline styles from rendered page: {filename}")
                    else:
                        logger.info(f"✅ Extracted CSS from browser: {filename}")
                else:
                    # Try fetching via browser context (authenticated)
                    try:
                        response = await page.request.get(css_url)
                        if response.ok:
                            content = await response.text()
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            logger.info(f"✅ Extracted CSS via browser fetch: {filename}")
                        else:
                            logger.warning(f"⚠️ Could not fetch CSS {css_url}: HTTP {response.status}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not fetch CSS {css_url}: {e}")
        
        except Exception as e:
            logger.error(f"Error extracting CSS from {url}: {e}")
    
    async def cleanup(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("✓ Browser closed")


class SPADetector:
    """Detect if a page needs JavaScript rendering."""
    
    SPA_INDICATORS = [
        'react', '__react', 'v-app', 'ng-app', '__next_data__',
        'ember-application', 'redux', 'vuex', '__nuxt__', '_next',
        '_app', 'root', '__layout'
    ]
    
    EMPTY_BODY_THRESHOLD = 200
    
    @staticmethod
    async def is_spa(url: str, html: str) -> bool:
        """Detect if page is a Single-Page Application."""
        html_lower = html.lower()
        
        for indicator in SPADetector.SPA_INDICATORS:
            if indicator in html_lower:
                logger.debug(f"SPA indicator detected: {indicator}")
                return True
        
        soup = BeautifulSoup(html, 'html.parser')
        body = soup.find('body')
        
        if body:
            body_text = body.get_text(strip=True)
            if len(body_text) < SPADetector.EMPTY_BODY_THRESHOLD:
                root_divs = soup.find(id=['root', 'app', '__next', '__nuxt'])
                if root_divs and len(root_divs.get_text(strip=True)) < 50:
                    logger.debug(f"Empty body with root div detected")
                    return True
        
        return False


def get_rendering_strategy(config: dict) -> RenderingStrategy:
    """
    Get rendering strategy based on configuration.
    
    Args:
        config: Configuration dict with 'javascript_rendering' section
        
    Returns:
        RenderingStrategy instance
    """
    js_config = config.get('javascript_rendering', {})
    enabled = js_config.get('enabled', False)
    
    if not enabled:
        logger.debug("Using StaticRenderingStrategy (JS rendering disabled)")
        return StaticRenderingStrategy()
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("Playwright not available. Falling back to static rendering.")
        return StaticRenderingStrategy()
    
    logger.info("Using PlaywrightRenderingStrategy")
    return PlaywrightRenderingStrategy(
        headless=js_config.get('headless', True),
        timeout=js_config.get('timeout', 30000)
    )
