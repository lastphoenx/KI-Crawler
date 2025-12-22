"""
HTML Documentation Generator
Creates a navigable HTML version of crawled documentation.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime
from urllib.parse import urlparse, urljoin, unquote, quote
import html
import asyncio
import aiohttp
import re
import hashlib
import uuid
import gc
import base64
from bs4 import BeautifulSoup
from jinja2 import Template

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """Generate navigable HTML documentation from crawled pages"""
    
    def __init__(self, config: Dict[str, Any], min_content_length: int = 20):
        self.config = config
        self.base_url = config.get('crawler', {}).get('entry_url', '')
        self.min_content_length = min_content_length  # Configurable threshold
        self.css_files: Set[str] = set()  # Track CSS files to download
        
        # Crawl statistics for structured logging
        self.crawl_stats = {
            'pages_parsed': [],
            'pages_duplicated': [],
            'downloads_success': [],
            'downloads_failed': [],
            'downloads_skipped': [],  # Too large, etc.
            'internal_links_created': [],
            'css_extracted': [],
            'css_failed': []
        }
    
    def generate(self, pages: Dict[str, Dict], output_dir: Path, base_name: str = 'index', enhanced_formatting: bool = False, extra_css_urls: List[str] = None, use_fallback_css: bool = False):
        """
        Generate HTML documentation
        
        Args:
            pages: Dict of {url: {'raw_html': html_content}}
            output_dir: Directory to save HTML files
            base_name: Base name for index file
            enhanced_formatting: Use enhanced HTML formatting with heuristics
        """
        try:
            logger.info(f"Generating HTML documentation to {output_dir}")
            logger.info(f"🔍 DEBUG: enhanced_formatting parameter = {enhanced_formatting}")
            
            if enhanced_formatting:
                logger.info("📊 Using enhanced HTML formatting with structure detection")
            else:
                logger.info("⚠️ Enhanced formatting DISABLED (enhanced_formatting=False)")
            
            # Create assets directory for CSS
            assets_dir = output_dir / 'assets'
            assets_dir.mkdir(exist_ok=True)
            
            # CSS handling: Extract if enhanced, fallback if requested, or both
            inline_styles = []
            
            if enhanced_formatting or use_fallback_css:
                if enhanced_formatting:
                    logger.info("🎨 Extracting CSS files from pages...")
                    inline_styles = self._extract_css_links(pages, use_fallback_css=use_fallback_css)
                elif use_fallback_css:
                    logger.info("🌟 Using fallback CSS (extraction disabled)")
                    self._add_fallback_css()
                
                # Add extra CSS URLs if provided
                if extra_css_urls:
                    logger.info(f"➕ Adding {len(extra_css_urls)} extra CSS URLs from user input...")
                    for css_url in extra_css_urls:
                        if css_url.strip():
                            self.css_files.add(css_url.strip())
                            logger.info(f"  ➕ Extra CSS: {css_url.strip()}")
                
                # Save inline styles
                if inline_styles:
                    inline_css_file = assets_dir / 'inline.css'
                    with open(inline_css_file, 'w', encoding='utf-8') as f:
                        f.write('\n\n'.join(inline_styles))
                    logger.info(f"💾 Saved {len(inline_styles)} inline CSS blocks to {inline_css_file}")
                
                # Download external CSS files
                if self.css_files:
                    logger.info(f"📥 Downloading {len(self.css_files)} CSS files...")
                    asyncio.run(self._download_css_files(assets_dir))
            
            # Generate custom CSS
            self._generate_css(assets_dir)
            
            # Parse pages to extract titles and content
            parsed_pages = self._parse_pages(pages, enhanced_formatting=enhanced_formatting)
            
            # Deduplicate identical pages based on content hash
            parsed_pages, duplicate_info = self._deduplicate_pages(parsed_pages)
            if duplicate_info:
                logger.info(f"🔄 Removed {len(duplicate_info)} duplicate pages")
                for original_title, duplicate_titles in duplicate_info.items():
                    logger.info(f"  📋 '{original_title}' had {len(duplicate_titles)} duplicate(s)")
            
            # ✅ FIX: Assign page IDs BEFORE link processing (not in _generate_index)
            for i, page in enumerate(parsed_pages):
                page['id'] = f"page-{i}"
            
            # Process page links in SINGLE pass (downloads + internal links)
            downloads_dir = output_dir / 'downloads'
            downloads_dir.mkdir(exist_ok=True)
            parsed_pages = asyncio.run(self._process_page_links(
                parsed_pages, 
                downloads_dir,
                max_file_size_mb=50  # Configurable limit
            ))
            
            # Log statistics summary
            self._log_crawl_statistics()
            
            # Generate index.html with navigation
            index_file = output_dir / f'{base_name}.html'
            self._generate_index(parsed_pages, index_file, assets_dir, enhanced_formatting)
            
            logger.info(f"✅ Generated HTML documentation: {index_file}")
            
            # Generate standalone version if requested (inline CSS/images/fonts as Base64)
            standalone_enabled = self.config.get('output', {}).get('inline_standalone', False)
            if standalone_enabled:
                logger.info("📦 Generating standalone version with inline assets...")
                standalone_file = output_dir / f'{base_name}-standalone.html'
                self._generate_standalone_html(index_file, standalone_file, assets_dir)
                logger.info(f"✅ Generated standalone HTML: {standalone_file}")
            
            return str(index_file)
            
        except Exception as e:
            logger.error(f"Failed to generate HTML: {e}", exc_info=True)
            return None
    
    def _parse_pages(self, pages: Dict[str, Dict], enhanced_formatting: bool = False) -> List[Dict]:
        """Parse pages to extract title and clean content"""
        from bs4 import BeautifulSoup
        
        parsed = []
        for url, page_data in pages.items():
            html_content = page_data.get('raw_html', '')
            if not html_content:
                continue
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title - try multiple strategies
            title = self._extract_page_title(soup, url)
            
            # Extract main content
            if enhanced_formatting:
                content = self._extract_content_enhanced(soup)
            else:
                content = self._extract_content(soup)
            
            # Use original_url if available for display/logging, normalized for keys
            original_url = page_data.get('original_url', url)
            
            parsed.append({
                'url': url,  # Normalized URL (for deduplication)
                'original_url': original_url,  # Original URL (for display)
                'title': title,
                'content': content,
                'html': html_content
            })
        
        return parsed
    
    def _extract_css_links(self, pages: Dict[str, Dict], use_fallback_css: bool = False) -> List[str]:
        """Extract all CSS file links and inline styles from HTML pages"""
        from bs4 import BeautifulSoup
        
        inline_styles = []
        pages_scanned = 0
        css_links_found = 0
        
        logger.info(f"🔎 Scanning {len(pages)} pages for CSS links... (fallback: {'ENABLED' if use_fallback_css else 'DISABLED'})")
        
        for url, page_data in pages.items():
            html_content = page_data.get('raw_html', '')
            if not html_content:
                continue
            
            pages_scanned += 1
            page_css_count = 0
            
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all <link> tags with rel="stylesheet"
                for link in soup.find_all('link', rel='stylesheet'):
                    href = link.get('href')
                    if href:
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(url, href)
                        if absolute_url not in self.css_files:
                            self.css_files.add(absolute_url)
                            css_links_found += 1
                            page_css_count += 1
                            logger.info(f"  📎 Found CSS: {absolute_url}")
                
                # Extract all <style> tags and save as inline CSS (with deduplication)
                for style in soup.find_all('style'):
                    # ✅ FIX: Use get_text() instead of .string to handle all content types
                    content = style.get_text(strip=False)
                    if content and content.strip():
                        # Deduplicate: Use hash to avoid storing identical CSS blocks
                        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                        
                        # Check if we've seen this exact CSS block before
                        if not hasattr(self, '_inline_css_hashes'):
                            self._inline_css_hashes = set()
                        
                        if content_hash not in self._inline_css_hashes:
                            self._inline_css_hashes.add(content_hash)
                            inline_styles.append(content)
                            logger.info(f"  📝 Found inline <style> tag ({len(content)} chars, unique)")
                        else:
                            logger.debug(f"  ⏭️ Skipped duplicate inline <style> tag ({len(content)} chars)")
                        
                        # Also check for @import in <style> tags
                        imports = re.findall(r'@import\s+["\']([^"\']+)["\']', content)
                        for css_url in imports:
                            absolute_url = urljoin(url, css_url)
                            if absolute_url not in self.css_files:
                                self.css_files.add(absolute_url)
                                css_links_found += 1
                                page_css_count += 1
                                logger.debug(f"Found @import CSS: {absolute_url}")
                
                if page_css_count > 0:
                    logger.debug(f"  ✓ Page {pages_scanned}: Found {page_css_count} CSS files")
            
            except Exception as e:
                logger.warning(f"Failed to extract CSS from {url}: {e}")
        
        # Log summary
        logger.info(f"✅ CSS scan complete: {pages_scanned} pages scanned, {css_links_found} unique CSS files found")
        if inline_styles:
            logger.info(f"📝 Found {len(inline_styles)} inline <style> tags")
        
        # Fallback: if no CSS found and user enabled it
        if use_fallback_css:
            if not self.css_files and not inline_styles:
                logger.warning(f"⚠️ No CSS files or inline styles found - using fallback CSS list (enabled by user)")
                self._add_fallback_css()
            elif not self.css_files and inline_styles:
                logger.warning(f"⚠️ No external CSS files found, but inline styles present - adding fallback URLs (enabled by user)")
                self._add_fallback_css()
        else:
            if not self.css_files:
                logger.info(f"ℹ️ No CSS files extracted (fallback disabled - this is expected during testing)")
        
        logger.info(f"📊 Total CSS files to download: {len(self.css_files)}")
        return inline_styles
    
    def _add_fallback_css(self):
        """Add known pCloud CSS files as fallback"""
        fallback_urls = [
            urljoin(self.base_url, '/css/api.css'),
            urljoin(self.base_url, '/css/site.css'),
            urljoin(self.base_url, '/css/docs.css'),
            urljoin(self.base_url, '/css/styles.css'),
            urljoin(self.base_url, '/css/main.css'),
            urljoin(self.base_url, '/css/documentation.css'),
            urljoin(self.base_url, '/assets/css/main.css'),
            urljoin(self.base_url, '/assets/css/style.css'),
            'https://v2.pcloud.com/dist/css/common.css',
            'https://v2.pcloud.com/dist/css/global.css',
            'https://v2.pcloud.com/dist/css/api.css',
            'https://v2.pcloud.com/dist/css/docs.css',
            'https://docs.pcloud.com/css/main.css',
            'https://docs.pcloud.com/css/api.css',
            'https://docs.pcloud.com/css/docs.css',
            'https://docs.pcloud.com/css/style.css',
            'https://docs.pcloud.com/assets/css/main.css',
            'https://pcloud.com/css/main.css',
            'https://pcloud.com/assets/css/style.css',
        ]
        
        logger.info(f"🌟 Adding {len(fallback_urls)} fallback CSS URLs for pCloud...")
        for css_url in fallback_urls:
            self.css_files.add(css_url)
            logger.info(f"  ➕ Fallback CSS: {css_url}")
    
    async def _download_css_files(self, assets_dir: Path):
        """Try to download CSS files via HTTP, with fallback to browser extraction"""
        # First try HTTP download
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/css,*/*;q=0.1',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': self.base_url
        }
        
        failed_urls = []
        
        # ✅ Session Pooling: Single session with connection limits
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
            tasks = []
            for css_url in self.css_files:
                tasks.append(self._download_single_css(session, css_url, assets_dir))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect failed URLs
            for css_url, result in zip(self.css_files, results):
                if result is not True:
                    failed_urls.append(css_url)
            
            success_count = len(self.css_files) - len(failed_urls)
            logger.info(f"✅ Successfully downloaded {success_count}/{len(self.css_files)} CSS files via HTTP (pooled session)")
        
        # Try browser extraction for failed URLs
        if failed_urls:
            logger.info(f"🌐 Attempting to extract {len(failed_urls)} CSS file(s) via browser...")
            success_count_browser = await self._extract_css_via_browser(failed_urls, assets_dir)
            logger.info(f"✅ Successfully extracted {success_count_browser}/{len(failed_urls)} CSS files via browser")
    
    async def _extract_css_via_browser(self, css_urls: list, assets_dir: Path) -> int:
        """Extract CSS files using Playwright browser context"""
        strategy = None
        try:
            from rendering_strategy import PlaywrightRenderingStrategy, PLAYWRIGHT_AVAILABLE
            
            if not PLAYWRIGHT_AVAILABLE:
                logger.warning("⚠️ Playwright not available for CSS extraction")
                return 0
            
            strategy = PlaywrightRenderingStrategy(headless=True)
            await strategy._ensure_browser()
            
            success_count = 0
            
            for css_url in css_urls:
                page = None
                try:
                    # Create a page and fetch CSS
                    page = await strategy.browser.new_page()
                    
                    response = await page.request.get(css_url)
                    if response.ok:
                        content = await response.text()
                        
                        # Generate filename - use UUID5 to avoid hash collisions
                        parsed = urlparse(css_url)
                        filename = Path(parsed.path).name
                        if not filename or not filename.endswith('.css'):
                            file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, css_url))[:8]
                            filename = f"style_{file_id}.css"
                        
                        output_path = assets_dir / filename
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        logger.debug(f"✅ Extracted CSS via browser: {filename}")
                        self.crawl_stats['css_extracted'].append(filename)
                        success_count += 1
                    else:
                        self.crawl_stats['css_failed'].append(f"{css_url} (HTTP {response.status})")
                        logger.warning(f"⚠️ Browser extraction failed for {css_url}: HTTP {response.status}")
                        
                except Exception as e:
                    self.crawl_stats['css_failed'].append(f"{css_url} ({str(e)})")
                    logger.warning(f"⚠️ Error extracting {css_url} via browser: {e}")
                finally:
                    if page:
                        await page.close()
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to extract CSS via browser: {e}")
            return 0
        finally:
            # Ensure complete cleanup: browser AND playwright process
            if strategy:
                try:
                    if hasattr(strategy, 'browser') and strategy.browser:
                        await strategy.browser.close()
                        logger.debug("✓ Browser closed")
                    if hasattr(strategy, 'playwright') and strategy.playwright:
                        await strategy.playwright.stop()
                        logger.debug("✓ Playwright process stopped")
                except Exception as cleanup_error:
                    logger.error(f"Error during browser cleanup: {cleanup_error}")
    
    def _safe_css_filename(self, css_url: str) -> str:
        """Generate safe CSS filename from URL"""
        parsed = urlparse(css_url)
        name = Path(unquote(parsed.path)).name
        
        if not name or "." not in name:
            # Fallback: SHA256 hash if URL has no filename
            h = hashlib.sha256(css_url.encode("utf-8")).hexdigest()[:16]
            name = f"style_{h}.css"
        elif not name.lower().endswith(".css"):
            # Add .css extension if missing
            name = name + ".css"
        
        return name
    
    async def _download_single_css(self, session: aiohttp.ClientSession, css_url: str, assets_dir: Path) -> bool:
        """Download a single CSS file via aiohttp (HTTP-only, no browser)"""
        HTML_MIMES = {"text/html", "application/xhtml+xml"}
        
        assets_dir.mkdir(parents=True, exist_ok=True)
        output_path = assets_dir / self._safe_css_filename(css_url)
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(css_url, timeout=timeout, allow_redirects=True) as response:
                if response.status != 200:
                    logger.warning(f"⚠️ CSS download failed (HTTP {response.status}): {css_url}")
                    return False
                
                # Check Content-Type: HTML means login page or error, NOT CSS
                ctype = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                if ctype in HTML_MIMES:
                    logger.warning(f"⚠️ Got HTML instead of CSS: {css_url}")
                    return False
                
                # ✅ BONUS: Use response.text() with charset detection, fallback to manual decode
                try:
                    text = await response.text()
                except UnicodeDecodeError:
                    raw = await response.read()
                    text = raw.decode("utf-8", errors="replace")
            
            # HTML sniff (additional safety check)
            sniff = text.lstrip().lower()
            if sniff.startswith("<!doctype") or sniff.startswith("<html") or sniff.startswith("<"):
                logger.warning(f"⚠️ Body looks like HTML, not CSS: {css_url}")
                return False
            
            await asyncio.to_thread(output_path.write_text, text, encoding="utf-8")
            logger.debug(f"✅ Downloaded CSS: {output_path.name}")
            return True
        
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Timeout downloading CSS: {css_url}")
            return False
        except aiohttp.ClientError as e:
            logger.warning(f"⚠️ HTTP error downloading CSS {css_url}: {e}")
            return False
        except Exception as e:
            logger.exception(f"⚠️ Unexpected error downloading CSS {css_url}: {e}")
            return False
    
    def _extract_page_title(self, soup, url: str) -> str:
        """Extract meaningful page title from soup with improved fallback logic"""
        from urllib.parse import urlparse, unquote
        
        # Generic titles to avoid
        GENERIC_TITLES = {
            'module/aufgaben/ergebnisse',
            'module',
            'aufgaben',
            'ergebnisse',
            'documentation',
            'home',
            'index'
        }
        
        # Try h1 first (most specific)
        for h_level in range(1, 4):
            h_elem = soup.find(f'h{h_level}')
            if h_elem:
                h_text = h_elem.get_text(strip=True)
                if h_text and h_text.lower() not in GENERIC_TITLES:
                    return h_text
        
        # Try title tag (but skip if generic)
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            # Often contains " | Site Name", split it
            if ' | ' in title_text:
                title_text = title_text.split(' | ')[0].strip()
            if title_text and title_text.lower() not in GENERIC_TITLES:
                return title_text
        
        # Fallback: Extract from URL path
        path = urlparse(url).path
        parts = [p for p in path.split('/') if p and p not in ['de', 'en', 'fr', 'it']]
        if parts:
            # Take last meaningful part
            filename = parts[-1].replace('.html', '').replace('.php', '')
            title = unquote(filename).replace('-', ' ').replace('_', ' ').title()
            return title
        
        return 'Untitled'
    
    def _extract_content_enhanced(self, soup) -> str:
        """Extract content with enhanced formatting - preserves HTML structure"""
        from copy import deepcopy
        
        soup_copy = deepcopy(soup)
        
        # Remove scripts and styles
        for script in soup_copy(["script", "style"]):
            script.decompose()
        
        # Remove navigation, header, footer
        for nav in soup_copy(["nav", "footer", "header"]):
            nav.decompose()
        
        # Remove breadcrumbs (common class names)
        for breadcrumb in soup_copy.find_all(['nav', 'div', 'ol', 'ul'], class_=lambda x: x and any(bc in x.lower() for bc in ['breadcrumb', 'breadcrumbs', 'path'])):
            breadcrumb.decompose()
        
        # Remove sidebars and aside elements
        for aside in soup_copy.find_all(['aside', 'div'], class_=lambda x: x and any(s in x.lower() for s in ['sidebar', 'side-bar', 'aside'])):
            aside.decompose()
        
        # Remove footer-like divs (often contain "Weitere Informationen" etc.)
        for footer_like in soup_copy.find_all('div', class_=lambda x: x and any(f in x.lower() for f in ['footer', 'foot', 'site-footer', 'page-footer'])):
            footer_like.decompose()
        
        # Remove "Weitere Informationen" and similar sections by text content
        for section in soup_copy.find_all(['div', 'section', 'aside']):
            section_text = section.get_text(strip=True).lower()
            if any(noise in section_text for noise in ['weitere informationen', 'über hermes', 'newsletter', 'änderungen vorschlagen', 'informieren']):
                # Only remove if it's a small section (< 200 chars = likely a link box)
                if len(section_text) < 200:
                    section.decompose()
        
        # Remove share buttons, social media
        for social in soup_copy.find_all(['div', 'section'], class_=lambda x: x and any(s in x.lower() for s in ['share', 'social', 'follow'])):
            social.decompose()
        
        # Find main content area
        main_content = (
            soup_copy.find('main') or 
            soup_copy.find('article') or 
            soup_copy.find('div', class_=lambda x: x and any(c in x.lower() for c in ['content', 'article', 'docs', 'documentation', 'main-content', 'post'])) or
            soup_copy.find('body')
        )
        
        if main_content:
            html_content = main_content.decode_contents() if hasattr(main_content, 'decode_contents') else str(main_content)
            return html_content
        
        return ''
    

    def _extract_content(self, soup) -> str:
        """Extract readable content from BeautifulSoup object"""
        from copy import deepcopy
        
        soup_copy = deepcopy(soup)
        
        # Remove scripts, styles, nav, footer, header
        for script in soup_copy(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Remove breadcrumbs
        for breadcrumb in soup_copy.find_all(['nav', 'div', 'ol', 'ul'], class_=lambda x: x and any(bc in x.lower() for bc in ['breadcrumb', 'breadcrumbs', 'path'])):
            breadcrumb.decompose()
        
        # Remove sidebars
        for aside in soup_copy.find_all(['aside', 'div'], class_=lambda x: x and any(s in x.lower() for s in ['sidebar', 'side-bar', 'aside'])):
            aside.decompose()
        
        # Remove footer-like divs
        for footer_like in soup_copy.find_all('div', class_=lambda x: x and any(f in x.lower() for f in ['footer', 'foot', 'site-footer', 'page-footer'])):
            footer_like.decompose()
        
        # Remove small "Weitere Informationen" sections
        for section in soup_copy.find_all(['div', 'section', 'aside']):
            section_text = section.get_text(strip=True).lower()
            if any(noise in section_text for noise in ['weitere informationen', 'über hermes', 'newsletter', 'änderungen vorschlagen']):
                if len(section_text) < 200:
                    section.decompose()
        
        # Remove dialogs and modals
        for elem in soup_copy(["dialog", "modal", "[role='dialog']"]):
            elem.decompose()
        
        # Get text from main content area
        main_content = (
            soup_copy.find('main') or 
            soup_copy.find('article') or 
            soup_copy.find('div', class_=lambda x: x and any(c in x.lower() for c in ['content', 'article', 'docs', 'documentation', 'main-content', 'post'])) or
            soup_copy.find('body')
        )
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
            if text and len(text) > 50:
                return text
        
        body = soup_copy.find('body')
        if body:
            text = body.get_text(separator='\n', strip=True)
            if text and len(text) > 50:
                return text
        
        return ''
    
    def _generate_css(self, assets_dir: Path):
        """Generate CSS stylesheet"""
        css_content = """
/* Modern Documentation Theme */
:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --bg-color: #ffffff;
    --sidebar-bg: #f8fafc;
    --border-color: #e2e8f0;
    --text-color: #1e293b;
    --code-bg: #f1f5f9;
    --hover-bg: #e0f2fe;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    color: var(--text-color);
    line-height: 1.6;
    display: flex;
    height: 100vh;
    overflow: hidden;
}

/* Sidebar Navigation */
.sidebar {
    width: 300px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border-color);
    overflow-y: auto;
    flex-shrink: 0;
}

.sidebar-header {
    padding: 1.5rem;
    border-bottom: 1px solid var(--border-color);
    background: white;
}

.sidebar-header h1 {
    font-size: 1.25rem;
    color: var(--primary-color);
    margin-bottom: 0.5rem;
}

.sidebar-header .meta {
    font-size: 0.875rem;
    color: var(--secondary-color);
}

.search-box {
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.search-box input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 0.875rem;
}

.nav-list {
    list-style: none;
    padding: 0.5rem 0;
}

.nav-item {
    padding: 0.5rem 1.5rem;
    cursor: pointer;
    transition: background 0.2s;
    border-left: 3px solid transparent;
    font-size: 0.875rem;
}

.nav-item:hover {
    background: var(--hover-bg);
}

.nav-item.active {
    background: var(--hover-bg);
    border-left-color: var(--primary-color);
    color: var(--primary-color);
    font-weight: 500;
}

/* Main Content Area */
.main-content {
    flex: 1;
    overflow-y: auto;
    padding: 2rem;
    background: var(--bg-color);
}

.content-container {
    max-width: 900px;
    margin: 0 auto;
}

.page-content {
    display: none;
}

.page-content.active {
    display: block;
    animation: fadeIn 0.3s;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.page-header {
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    padding-top: 1.5rem;
    border-bottom: 2px solid var(--border-color);
    border-top: 2px solid rgba(37, 99, 235, 0.1);
}

.page-title {
    font-size: 2.25rem;
    margin-bottom: 0.75rem;
    color: var(--primary-color);
    font-weight: 800;
}

.page-url {
    font-size: 0.875rem;
    color: var(--secondary-color);
    word-break: break-all;
    background: rgba(37, 99, 235, 0.05);
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    font-family: monospace;
}

/* Content Styling */
.page-content h1, .page-content h2, .page-content h3, 
.page-content h4, .page-content h5, .page-content h6 {
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    color: var(--text-color);
}

.page-content h1 { font-size: 1.875rem; }
.page-content h2 { font-size: 1.5rem; }
.page-content h3 { font-size: 1.25rem; }

.page-content p {
    margin-bottom: 1.25rem;
    line-height: 1.75;
    color: var(--text-color);
}

.page-content a {
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 500;
    border-bottom: 1px solid rgba(37, 99, 235, 0.3);
    transition: all 0.2s;
}

.page-content a:hover {
    color: #1e40af;
    border-bottom-color: #1e40af;
    background: rgba(37, 99, 235, 0.05);
}

.page-content code {
    background: var(--code-bg);
    padding: 0.3rem 0.5rem;
    border-radius: 4px;
    font-size: 0.9em;
    font-family: 'Courier New', Consolas, monospace;
    border: 1px solid var(--border-color);
}

.page-content pre {
    background: var(--code-bg);
    padding: 1.5rem;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1.5rem 0;
    border-left: 4px solid var(--primary-color);
    border: 1px solid var(--border-color);
}

.page-content pre code {
    background: none;
    padding: 0;
    font-size: 0.95em;
    line-height: 1.6;
}

.page-content table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    overflow: hidden;
}

.page-content th, .page-content td {
    padding: 1rem;
    border: 1px solid var(--border-color);
    text-align: left;
}

.page-content th {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    font-weight: 700;
    color: var(--primary-color);
}

.page-content tr:hover {
    background: rgba(37, 99, 235, 0.02);
}

.page-content ul, .page-content ol {
    margin: 1.5rem 0;
    padding-left: 2.5rem;
}

.page-content li {
    margin-bottom: 0.75rem;
    line-height: 1.7;
}

.page-content blockquote {
    border-left: 4px solid var(--primary-color);
    padding-left: 1.5rem;
    margin: 1.5rem 0;
    color: var(--secondary-color);
    font-style: italic;
}

.page-content strong {
    font-weight: 700;
    color: #003366;
}

/* Definition Lists */
.page-content dl {
    margin: 1.5rem 0;
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    overflow: hidden;
}

.page-content dt {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    font-weight: 700;
    color: var(--primary-color);
    padding: 1rem;
    border-right: 2px solid var(--border-color);
}

.page-content dd {
    padding: 1rem;
    margin: 0;
    color: var(--text-color);
}

.page-content dd:hover {
    background: rgba(37, 99, 235, 0.02);
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--sidebar-bg);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--secondary-color);
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 3rem;
    color: var(--secondary-color);
}

.empty-state h2 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
}
"""
        # ✅ Use 00-base.css so it loads FIRST (alphabetically)
        # Site-specific CSS (Main.css, Hermes.css) can then override our generic styles
        css_file = assets_dir / '00-base.css'
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        logger.info(f"Generated base CSS: {css_file}")
    
    def _generate_index(self, pages: List[Dict], output_file: Path, assets_dir: Path, enhanced_formatting: bool = False):
        """Generate index.html using Jinja2 template with improved navigation"""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from pathlib import Path as PathLib
        from urllib.parse import urlparse
        
        # Setup Jinja2 environment
        template_dir = PathLib(__file__).parent / 'templates'
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        template = env.get_template('index_template.html')
        
        # Build hierarchical navigation tree from URL structure
        nav_tree = self._build_navigation_tree(pages)
        
        # ✅ IDs are already set before link processing - just format content
        for page in pages:
            # Handle content formatting
            content = page['content']
            if content and not ('<' in content and '>' in content):
                # Plain text - format as preformatted
                content = f'<pre style="white-space: pre-wrap; font-family: inherit;">{html.escape(content)}</pre>'
            page['content'] = content
        
        # Collect CSS files - alphabetically sorted so 00-base.css loads first
        css_files = []
        if enhanced_formatting:
            for css_file in sorted(assets_dir.glob('*.css')):
                css_files.append(css_file.name)
        else:
            # If not enhanced formatting, still include base CSS
            if (assets_dir / '00-base.css').exists():
                css_files.append('00-base.css')
        
        # Determine first page ID for hash-based navigation
        first_page_id = pages[0]['id'] if pages else None
        
        # Render template
        html_content = template.render(
            title=f"Documentation - {self.base_url}",
            site_title="📚 Documentation",
            base_url=self.base_url,
            nav_tree=nav_tree,
            css_files=css_files,
            fallback_css=(assets_dir / 'fallback.css').exists(),
            generated_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
            first_page_id=first_page_id
        )
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_standalone_html(self, index_file: Path, output_file: Path, assets_dir: Path):
        """Generate standalone HTML with all assets inlined as Base64 (CSS, images, fonts)"""
        try:
            # Read the generated HTML
            with open(index_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            original_size = len(html_content)
            css_inlined_count = 0
            images_inlined_count = 0
            fonts_inlined_count = 0
            
            # STEP 1: Inline external CSS files
            for link_tag in soup.find_all('link', rel='stylesheet'):
                href = link_tag.get('href')
                if not href or href.startswith('data:'):
                    continue
                
                # Build full path to CSS file
                if href.startswith('assets/'):
                    css_path = assets_dir / href.replace('assets/', '')
                else:
                    css_path = assets_dir / href
                
                if css_path.exists():
                    try:
                        with open(css_path, 'r', encoding='utf-8') as f:
                            css_content = f.read()
                        
                        # Create <style> tag
                        style_tag = soup.new_tag('style', type='text/css')
                        style_tag.string = css_content
                        
                        # Replace <link> with <style>
                        link_tag.replace_with(style_tag)
                        css_inlined_count += 1
                        logger.debug(f"  📝 Inlined CSS: {css_path.name} ({len(css_content)} bytes)")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Failed to inline CSS {css_path}: {e}")
            
            # STEP 2: Convert images to Base64 data URLs
            for img_tag in soup.find_all('img'):
                src = img_tag.get('src')
                if not src or src.startswith('data:'):
                    continue
                
                # Build full path to image file
                if src.startswith('assets/'):
                    img_path = assets_dir / src.replace('assets/', '')
                elif src.startswith('/'):
                    img_path = assets_dir / src.lstrip('/')
                else:
                    img_path = assets_dir / src
                
                if img_path.exists():
                    try:
                        # Detect MIME type from extension
                        ext = img_path.suffix.lower()
                        mime_types = {
                            '.png': 'image/png',
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.gif': 'image/gif',
                            '.webp': 'image/webp',
                            '.svg': 'image/svg+xml'
                        }
                        mime_type = mime_types.get(ext, 'application/octet-stream')
                        
                        # Read image and convert to Base64
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                        
                        b64_data = base64.b64encode(img_data).decode('utf-8')
                        data_url = f'data:{mime_type};base64,{b64_data}'
                        
                        img_tag['src'] = data_url
                        images_inlined_count += 1
                        logger.debug(f"  🖼️ Inlined image: {img_path.name} ({len(img_data)} bytes → {len(b64_data)} Base64)")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Failed to inline image {img_path}: {e}")
            
            # STEP 3: Convert @font-face URLs to Base64 in CSS (within <style> tags)
            for style_tag in soup.find_all('style'):
                style_content = style_tag.string
                if not style_content:
                    continue
                
                # Find all url() references in the CSS (fonts, background-images, etc.)
                font_pattern = r"url\(['\"]?([^'\"()]+)['\"]?\)"
                matches = list(re.finditer(font_pattern, style_content))
                
                # Process in reverse order to preserve indices
                for match in reversed(matches):
                    url_ref = match.group(1)
                    
                    # Skip data: URLs and external URLs
                    if url_ref.startswith('data:') or url_ref.startswith('http'):
                        continue
                    
                    # Build full path to font file
                    if url_ref.startswith('assets/'):
                        font_path = assets_dir / url_ref.replace('assets/', '')
                    elif url_ref.startswith('/'):
                        font_path = assets_dir / url_ref.lstrip('/')
                    else:
                        font_path = assets_dir / url_ref
                    
                    if font_path.exists():
                        try:
                            # Detect MIME type from extension
                            ext = font_path.suffix.lower()
                            mime_types = {
                                '.woff2': 'font/woff2',
                                '.woff': 'font/woff',
                                '.ttf': 'font/ttf',
                                '.otf': 'font/otf',
                                '.eot': 'application/vnd.ms-fontobject'
                            }
                            mime_type = mime_types.get(ext, 'application/octet-stream')
                            
                            # Read font and convert to Base64
                            with open(font_path, 'rb') as f:
                                font_data = f.read()
                            
                            b64_data = base64.b64encode(font_data).decode('utf-8')
                            data_url = f'data:{mime_type};base64,{b64_data}'
                            
                            # Replace URL in CSS
                            style_content = (
                                style_content[:match.start(1)] +
                                data_url +
                                style_content[match.end(1):]
                            )
                            fonts_inlined_count += 1
                            logger.debug(f"  🔤 Inlined font: {font_path.name} ({len(font_data)} bytes → {len(b64_data)} Base64)")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Failed to inline font {font_path}: {e}")
                
                # Update the style tag with modified content
                if style_content:
                    style_tag.string = style_content
            
            # Write standalone HTML
            standalone_content = str(soup.prettify())
            standalone_size = len(standalone_content)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(standalone_content)
            
            # Log statistics
            size_increase = standalone_size - original_size
            size_increase_pct = (size_increase / original_size * 100) if original_size > 0 else 0
            
            logger.info(f"  📊 Standalone statistics:")
            logger.info(f"     Original: {original_size / 1024:.1f} KB")
            logger.info(f"     Standalone: {standalone_size / 1024:.1f} KB ({size_increase_pct:+.1f}%)")
            logger.info(f"     Inlined assets: {css_inlined_count} CSS + {images_inlined_count} images + {fonts_inlined_count} fonts")
            
        except Exception as e:
            logger.error(f"Failed to generate standalone HTML: {e}", exc_info=True)
    
    def _build_navigation_tree(self, pages: List[Dict]) -> List[Dict]:
        """Build hierarchical navigation tree from URL paths
        Returns list of root nodes, each with 'name', 'pages', and 'children' keys
        """
        from urllib.parse import urlparse
        from collections import defaultdict
        
        # Build tree structure
        root_children = {}
        
        for page in pages:
            url = page['url']
            parsed = urlparse(url)
            # Remove language codes and empty segments
            path_parts = [p for p in parsed.path.split('/') if p and p not in ['de', 'en', 'fr', 'it']]
            
            if not path_parts:
                continue
            
            # Remove file extensions from last part (e.g., "page.html" → "page")
            if path_parts:
                last_part = path_parts[-1]
                for ext in ['.html', '.htm', '.php', '.asp', '.aspx', '.jsp']:
                    if last_part.lower().endswith(ext):
                        path_parts[-1] = last_part[:last_part.lower().rfind(ext)]
                        break
            
            if not path_parts:
                continue
            
            # Build folder hierarchy
            current = root_children
            
            # Navigate through ALL path parts, creating folders as needed
            for part in path_parts:
                if part not in current:
                    current[part] = {'pages': [], 'children': {}}
                # If this is the last part, add page here and stop
                if part == path_parts[-1]:
                    current[part]['pages'].append(page)
                    break
                # Otherwise navigate deeper
                current = current[part]['children']
        
        # Convert dict tree to list structure for template
        def dict_to_list(node_dict, sort_key=None):
            result = []
            for name, node in sorted(node_dict.items()):
                nice_name = name.replace('-', ' ').replace('_', ' ').title()
                result.append({
                    'name': nice_name,
                    'pages': sorted(node['pages'], key=lambda p: p['title']) if node['pages'] else [],
                    'children': dict_to_list(node['children'])
                })
            return result
        
        return dict_to_list(root_children)
    
    def _deduplicate_pages(self, pages: List[Dict]) -> Tuple[List[Dict], Dict[str, List[str]]]:
        """Remove duplicate pages based on content hash AND filter out near-empty pages"""
        seen_hashes = {}
        unique_pages = []
        duplicates = {}
        empty_pages = []
        
        for page in pages:
            # Calculate SHA256 hash of content
            content = page.get('content', '')
            
            # Filter out near-empty pages (footer-only pages)
            # Extract text without HTML tags for length check
            soup = BeautifulSoup(content, 'html.parser')
            text_only = soup.get_text(strip=True)
            del soup  # Clean up
            
            # Configurable threshold (0 = disable filtering)
            if self.min_content_length > 0 and len(text_only) < self.min_content_length:
                empty_pages.append(page['title'])
                logger.debug(f"⏭️ Skipping near-empty page: '{page['title']}' ({len(text_only)} chars < {self.min_content_length} threshold)")
                continue
            
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            if content_hash in seen_hashes:
                # Duplicate found
                original_title = seen_hashes[content_hash]['title']
                duplicate_title = page['title']
                
                if original_title not in duplicates:
                    duplicates[original_title] = []
                duplicates[original_title].append(duplicate_title)
                
                logger.debug(f"🔄 Duplicate detected: '{duplicate_title}' is identical to '{original_title}'")
            else:
                # New unique page
                seen_hashes[content_hash] = page
                unique_pages.append(page)
        
        # Log summary of filtered pages
        if empty_pages:
            if self.min_content_length > 0:
                logger.info(f"⏭️ Filtered {len(empty_pages)} near-empty pages (< {self.min_content_length} chars, configurable via min_content_length)")
            else:
                logger.info(f"⏭️ Empty page filtering DISABLED (min_content_length=0)")
        
        return unique_pages, duplicates
    
    async def _process_page_links(self, pages: List[Dict], downloads_dir: Path, max_file_size_mb: int = 50) -> List[Dict]:
        """Process all page links in SINGLE pass: downloads + internal references"""
        # Separate semaphores: HEAD requests can be more parallel than downloads
        head_semaphore = asyncio.Semaphore(20)  # Fast HEAD requests
        download_semaphore = asyncio.Semaphore(3)  # Slow downloads
        
        download_extensions = {
            # PDF
            '.pdf',
            # Microsoft Office (current)
            '.docx', '.xlsx', '.pptx',
            # Microsoft Office (legacy)
            '.doc', '.xls', '.ppt',
            # Microsoft Office Templates
            '.dotx', '.xltx', '.potx', '.dot', '.xlt', '.pot',
            # Archives
            '.zip', '.rar', '.7z', '.tar', '.gz',
            # Other documents
            '.odt', '.ods', '.odp',  # OpenOffice/LibreOffice
            '.rtf', '.txt', '.csv'
        }
        
        logger.info(f"🔍 Scanning {len(pages)} pages for downloadable files...")
        
        # Build indexes for internal linking (do once, not per page)
        title_to_id = {page['title'].lower(): page.get('id', '') for page in pages}
        url_to_id = {}
        for page in pages:
            parsed = urlparse(page['url'])
            slug = Path(parsed.path).stem
            url_to_id[slug.lower()] = page.get('id', '')
        
        # ✅ FIX: Create ONE session for all link checks (performance + rate-limit)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Process each page
            for page in pages:
                content = page.get('content', '')
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all links (process once per page)
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    link_text = link.get_text(strip=False)
                    
                    # STAGE 1: Lightweight candidate scoring (cheap HTML-based pre-filter)
                    candidate_score = self._score_download_candidate(href, link_text, link)
                    
                    # Skip if score too low (< 2 = definitely not worth checking)
                    if candidate_score < 2:
                        # Treat as internal link
                        link_text_lower = link_text.strip().lower()
                        
                        # Match by title
                        if link_text_lower in title_to_id:
                            target_id = title_to_id[link_text_lower]
                            link['href'] = f"#{target_id}"
                            # Hash-Navigation: kein onclick, Browser setzt Hash automatisch
                            self.crawl_stats['internal_links_created'].append(f"{link_text_lower} → {target_id}")
                        
                        # Match by URL slug
                        elif href and not href.startswith(('http://', 'https://', '#')):
                            slug = Path(urlparse(href).path).stem.lower()
                            if slug in url_to_id:
                                target_id = url_to_id[slug]
                                link['href'] = f"#{target_id}"
                                # Hash-Navigation: kein onclick, Browser setzt Hash automatisch
                                self.crawl_stats['internal_links_created'].append(f"{slug} → {target_id}")
                        continue
                    
                    # STAGE 2: Server verification
                    # ✅ FIX: Prüfe ob URL bereits absolut ist
                    if href.startswith(('http://', 'https://')):
                        # Absolute URL → direkt verwenden, NICHT verarbeiten!
                        absolute_url = href
                    else:
                        # Nur relative URLs verarbeiten
                        decoded_href = unquote(href)
                        absolute_url = urljoin(page['url'], decoded_href)
                    
                    # Low-medium score (2-4): Quick HEAD check first (10-20x faster!)
                    if candidate_score < 5:
                        async with head_semaphore:
                            status, check_reason = await self._quick_head_check(session, absolute_url, page['url'])
                        
                        # If HEAD fails or returns 404/403, log and skip
                        if status in [404, 403, 410]:
                            logger.info(f"⚠️ Broken link: {absolute_url} (found on page: {page['url']}) - HTTP {status}")
                            self.crawl_stats['downloads_failed'].append(f"{absolute_url} (HTTP {status})")
                            continue
                        elif status == 0:  # Timeout/error
                            logger.debug(f"⚠️ HEAD check failed: {absolute_url} - {check_reason}")
                            # Fall through to full verification
                        elif status in range(200, 300):  # Success
                            # Might still be a download, check with full verification
                            pass
                    
                    # High score (≥5) or HEAD was inconclusive: Full download verification
                    async with download_semaphore:
                        is_download, reason = await self._verify_download_by_response(session, absolute_url, page['url'])
                    
                    if is_download:
                        # Server confirmed: It's a download!
                        logger.debug(f"📥 Download verified (score={candidate_score}): {href[:60]}...")
                        logger.debug(f"   Server says: {reason}")
                        
                        local_path, was_downloaded = await self._download_file_with_validation(
                            session,
                            absolute_url, 
                            downloads_dir,
                            max_size_mb=max_file_size_mb
                        )
                        
                        if local_path:
                            # URL-encode filename (spaces → %20, etc.) but keep '/' safe
                            # Handle potential surrogate errors in filename
                            try:
                                safe_filename = quote(local_path.name, safe='')
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                # If filename has encoding issues, use URL-safe version
                                safe_filename = quote(str(local_path.name).encode('utf-8', errors='ignore').decode('utf-8'), safe='')
                            link['href'] = f"downloads/{safe_filename}"
                            # Only count if actually downloaded (not cached)
                            if was_downloaded:
                                self.crawl_stats['downloads_success'].append(local_path.name)
                        else:
                            # Download failed after verification
                            self.crawl_stats['downloads_failed'].append(f"{absolute_url} (download failed)")
                            logger.warning(f"⚠️ Download failed: {absolute_url} (found on page: {page['url']})")
                    else:
                        # Server says NOT a download
                        logger.debug(f"⏭️ Not a download (score={candidate_score}): {reason}")
                        
                        # Log common errors at INFO level for visibility
                        if 'HTTP 404' in reason or 'HTTP 403' in reason or 'HTTP 500' in reason:
                            logger.info(f"⚠️ Download candidate failed: {href} (found on page: {page['url']}) - {reason}")
                            self.crawl_stats['downloads_failed'].append(f"{absolute_url} ({reason})")
                        link_text_lower = link_text.strip().lower()
                        
                        # Match by title (use lowercase for matching!)
                        if link_text_lower in title_to_id:
                            target_id = title_to_id[link_text_lower]
                            link['href'] = f"#{target_id}"
                            # Hash-Navigation: kein onclick, Browser setzt Hash automatisch
                            self.crawl_stats['internal_links_created'].append(f"{link_text_lower} → {target_id}")
                        
                        # Match by URL slug
                        elif href and not href.startswith(('http://', 'https://', '#')):
                            slug = Path(urlparse(href).path).stem.lower()
                            if slug in url_to_id:
                                target_id = url_to_id[slug]
                                link['href'] = f"#{target_id}"
                                # Hash-Navigation: kein onclick, Browser setzt Hash automatisch
                                self.crawl_stats['internal_links_created'].append(f"{slug} → {target_id}")
                
                # Update page content
                page['content'] = str(soup)
                
                # Explicit cleanup
                del soup
        
        # Force garbage collection
        gc.collect()
        
        return pages
    
    def _score_download_candidate(self, href: str, link_text: str, link_elem) -> int:
        """
        Lightweight scoring: Only check if it's worth verifying with server.
        No hard decisions - just prioritization.
        Returns: score (0-10+), threshold for verification is >= 2
        """
        score = 0
        parsed = urlparse(href)
        path = parsed.path.lower()
        query = parsed.query.lower() if parsed.query else ''
        text = link_text.lower()
        
        # HARD EXCLUSIONS (only pure HTML pages)
        file_ext = Path(path).suffix.lower()
        if file_ext in {'.html', '.htm'}:
            return 0
        
        # Image files: exclude UNLESS they have explicit download attribute
        # (Images are usually embedded, not downloads)
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}
        if file_ext in image_exts:
            # Only allow if explicit download attribute (HTML5)
            if link_elem.get('download') is None:
                return 0  # Hard exclusion for images without download attribute
            else:
                score += 5  # Bonus for explicit download attribute on image
        
        # Script extensions: negative weight (might be download controllers like download.php?id=...)
        if file_ext in {'.php', '.asp', '.aspx', '.jsp', '.cfm'}:
            score -= 2  # Penalty but NOT hard exclusion
        
        # Navigation texts: penalty, not hard exclusion
        exclusion_texts = {'home', 'startseite', 'kontakt', 'über uns', 'about', 'contact'}
        if any(excl in text for excl in exclusion_texts):
            score -= 3  # Strong penalty but allow server check if other signals present
        
        # URL-based signals
        if any(k in path for k in ('/download', '/downloads', '/files', '/uploads', '/media', '/vorlage')):
            score += 3
        if any(k in query for k in ('download=', 'file=', 'attachment=', 'asset=')):
            score += 2
        
        # File extension (bonus only)
        download_exts = {'.pdf', '.zip', '.rar', '.7z', '.csv', '.xlsx', '.xls', '.docx', '.doc', 
                        '.pptx', '.ppt', '.dotx', '.xltx', '.potx', '.mp3', '.mp4', '.png', 
                        '.jpg', '.jpeg', '.gif', '.exe', '.dmg', '.apk', '.odt', '.ods', '.rtf'}
        has_download_ext = file_ext in download_exts
        if has_download_ext:
            score += 5  # ERHÖHT von +3 auf +5: Context Penalty drückt nicht unter Threshold
        
        # Link text signals
        if any(k in text for k in ('download', 'herunterladen', 'télécharger', 'pdf', 'csv', 'export')):
            score += 2
        if re.search(r'\b\d+\.?\d*\s*(?:kb|mb|gb)\b', text, re.IGNORECASE):
            score += 2  # File size in text
        
        # HTML5 download attribute (VERY strong signal)
        if link_elem.get('download') is not None:
            score += 5
        
        # CSS classes
        link_classes = ' '.join(link_elem.get('class', [])).lower()
        if any(p in link_classes for p in ('download', 'attachment', 'file-link', 'asset')):
            score += 2
        
        # Download icon
        if link_elem.find(['svg', 'img'], class_=lambda x: x and 'download' in str(x).lower()):
            score += 1
        
        # Context penalty (footer/header)
        # ABER: Überspringe Penalty für Download-Extensions (sie sind überall gültig)
        if not has_download_ext and link_elem.find_parent(['main', 'article', 'section']) is None:
            score = int(score * 0.7)  # 30% penalty
        
        return score
    
    async def _quick_head_check(self, session: aiohttp.ClientSession, url: str, source_page_url: str = None) -> tuple[int, str]:
        """Fast HEAD request to check link validity (for non-download links)
        Returns: (status_code, reason)
        """
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as response:
                return (response.status, f"HTTP {response.status}")
        except asyncio.TimeoutError:
            return (0, "Timeout")
        except aiohttp.ClientError as e:
            return (0, f"Connection error: {str(e)[:40]}")
        except Exception as e:
            return (0, f"Error: {str(e)[:40]}")
    
    async def _verify_download_by_response(self, session: aiohttp.ClientSession, url: str, source_page_url: str = None) -> tuple[bool, str]:
        """
        SERVER-BASED VERIFICATION: The ground truth!
        Uses HEAD + Range GET + Magic Bytes to definitively determine if URL is a download.
        Returns: (is_download: bool, reason: str)
        """
        # Magic byte signatures
        MAGIC_BYTES = [
            (b'%PDF-', 'PDF'),
            (b'PK\x03\x04', 'ZIP'),
            (b'\x89PNG\r\n\x1a\n', 'PNG'),
            (b'\x1f\x8b', 'GZIP'),
            (b'GIF87a', 'GIF87a'),
            (b'GIF89a', 'GIF89a'),
            (b'\xff\xd8\xff', 'JPEG'),
            (b'PK', 'Office/ZIP'),  # Broader Office format check
        ]
        
        HTML_MIMES = {'text/html', 'application/xhtml+xml'}
        # Note: 'image/' removed - images are excluded by file extension check
        DOWNLOAD_MIME_PREFIXES = ('application/', 'audio/', 'video/', 'font/')
        
        try:
            # STEP 1: HEAD request (cheap) - but some servers return wrong Content-Type!
            # UniBas example: HEAD returns image/jpeg but GET returns application/pdf
            # Solution: Don't trust HEAD fully, always verify with GET + magic bytes
            head_suggested_download = False
            try:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=15), allow_redirects=True) as head_resp:
                    if head_resp.status == 200:
                        # Check Content-Disposition (strongest signal)
                        cdisp = head_resp.headers.get('Content-Disposition', '').lower()
                        if 'attachment' in cdisp or 'filename=' in cdisp:
                            head_suggested_download = True
                        
                        # Check Content-Type (but don't trust it fully!)
                        ctype = head_resp.headers.get('Content-Type', '').split(';')[0].strip().lower()
                        if ctype and ctype not in HTML_MIMES and any(ctype.startswith(p) for p in DOWNLOAD_MIME_PREFIXES):
                            head_suggested_download = True
            except:
                pass  # HEAD not supported, continue to GET
            
            # STEP 2: Range GET + Magic Bytes (authoritative check)
            # Always perform this check to verify actual file content
            headers = {'Range': 'bytes=0-2047'}  # Read first 2KB only
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20), allow_redirects=True) as get_resp:
                    if get_resp.status not in (200, 206):  # 206 = Partial Content
                        return False, f"HTTP {get_resp.status}"
                    
                    # Check Content-Disposition again (GET might have it even if HEAD didn't)
                    cdisp = get_resp.headers.get('Content-Disposition', '').lower()
                    if 'attachment' in cdisp or 'filename=' in cdisp:
                        return True, "Content-Disposition (GET): attachment/filename"
                    
                    ctype = get_resp.headers.get('Content-Type', '').split(';')[0].strip().lower()
                    
                    # Read first chunk for magic bytes
                    chunk = await get_resp.content.read(2048)
                    
                    # Magic byte detection
                    for sig, name in MAGIC_BYTES:
                        if chunk.startswith(sig):
                            return True, f"Magic bytes: {name}"
                    
                    # HTML detection (anti-pattern)
                    sample = chunk.lstrip()[:200].lower()
                    if sample.startswith((b'<!doctype', b'<html', b'<head', b'<body')):
                        return False, "HTML detected"
                    
                    # octet-stream + not HTML-like → likely download
                    if ctype == 'application/octet-stream' and not sample.startswith(b'<'):
                        return True, "octet-stream (non-HTML)"
                    
                    # ✅ FIX #5: Parse Content-Range for accurate file size (better than Content-Length)
                    crange = get_resp.headers.get('Content-Range')
                    if crange:
                        # Format: "bytes 0-2047/1234567" → extract 1234567
                        match = re.search(r'/(\d+)$', crange)
                        if match:
                            total_size = int(match.group(1))
                            if total_size > 200_000 and ctype not in HTML_MIMES:
                                return True, f"Large non-HTML ({total_size // 1024}KB via Content-Range)"
                    
                    # Fallback: Content-Length (less reliable for Range GET)
                    clen = get_resp.headers.get('Content-Length')
                    if clen and clen.isdigit() and int(clen) > 200_000 and ctype not in HTML_MIMES:
                        return True, f"Large non-HTML ({int(clen) // 1024}KB, type={ctype})"
                    
                    return False, f"Unclear (type={ctype or 'unknown'})"
        
        except asyncio.TimeoutError:
            source_info = f" (found on page: {source_page_url})" if source_page_url else ""
            logger.warning(f"⚠️ Timeout verifying {url}{source_info} - treating as potential download")
            return True, "Timeout (assumed download)"
        except Exception as e:
            source_info = f" (found on page: {source_page_url})" if source_page_url else ""
            logger.warning(f"⚠️ Server check failed for {url}{source_info}: {e}")
            return True, f"Error (assumed download): {str(e)[:40]}"
    
    async def _download_file_with_validation(self, session: aiohttp.ClientSession, url: str, output_dir: Path, max_size_mb: int = 50) -> tuple[Path, bool]:
        """Download file with size validation BEFORE downloading full content
        Returns: (file_path, was_actually_downloaded)
        """
        try:
            # Generate initial filename from URL (decode URL-encoding like %20 → space)
            parsed = urlparse(url)
            filename = unquote(Path(parsed.path).name)
            
            if not filename or filename in ['downloadvorlage', 'download', 'attachment', 'file']:
                # Controller endpoint - need to get filename from Content-Disposition header
                file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))[:8]
                filename = f"download_{file_id}.tmp"  # Temporary, will be replaced from header
            
            # Step 1: HEAD request to check file size AND get Content-Disposition
            filename_from_header = None
            try:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=20), allow_redirects=True) as head_response:
                    if head_response.status == 200:
                        # Extract filename from Content-Disposition header
                        content_disp = head_response.headers.get('Content-Disposition', '')
                        if content_disp:
                            # Parse: attachment; filename="document.docx" or filename*=UTF-8''document.docx
                            match = re.search(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';]+)', content_disp)
                            if match:
                                filename_from_header = unquote(match.group(1).strip())
                                logger.debug(f"📄 Extracted filename from header: {filename_from_header}")
                        
                        # Check file size
                        content_length = head_response.headers.get('Content-Length')
                        if content_length:
                            size_mb = int(content_length) / (1024 * 1024)
                            if size_mb > max_size_mb:
                                display_name = filename_from_header or filename
                                self.crawl_stats['downloads_skipped'].append(
                                    f"{display_name} ({size_mb:.1f}MB > {max_size_mb}MB limit)"
                                )
                                logger.debug(f"⏭️ Skipped {display_name}: {size_mb:.1f}MB exceeds limit")
                                return None
            except:
                # HEAD not supported, continue with GET
                pass
            
            # Use filename from header if available
            if filename_from_header:
                filename = filename_from_header
            
            # Sanitize filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            output_path = output_dir / filename
            
            # Skip if already downloaded
            if output_path.exists():
                logger.debug(f"✓ Already downloaded: {filename}")
                return (output_path, False)  # File exists, not downloaded now
            
            # Step 2: Download file
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60), allow_redirects=True) as response:
                if response.status == 200:
                    # Try to get filename from GET response if not from HEAD
                    if not filename_from_header:
                        content_disp = response.headers.get('Content-Disposition', '')
                        if content_disp:
                            match = re.search(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';]+)', content_disp)
                            if match:
                                filename_from_header = unquote(match.group(1).strip())
                                filename = re.sub(r'[<>:"/\\|?*]', '_', filename_from_header)
                                output_path = output_dir / filename
                                logger.debug(f"📄 Extracted filename from GET response: {filename}")
                    
                    content = await response.read()
                    
                    # Final size check
                    size_mb = len(content) / (1024 * 1024)
                    if size_mb > max_size_mb:
                        self.crawl_stats['downloads_skipped'].append(
                            f"{filename} ({size_mb:.1f}MB > {max_size_mb}MB limit)"
                        )
                        return None
                    
                    with open(output_path, 'wb') as f:
                        f.write(content)
                    
                    logger.debug(f"✅ Downloaded: {filename} ({size_mb:.2f}MB)")
                    return (output_path, True)  # File downloaded successfully
                else:
                    self.crawl_stats['downloads_failed'].append(
                        f"{filename} (HTTP {response.status})"
                    )
                    return (None, False)
        
        except Exception as e:
            error_msg = str(e)
            self.crawl_stats['downloads_failed'].append(f"{url} ({error_msg})")
            logger.warning(f"❌ Download failed: {url} - {error_msg}")
            return (None, False)
    
    def _log_crawl_statistics(self):
        """Log aggregated crawl statistics (instead of per-item logs)"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 CRAWL STATISTICS SUMMARY")
        logger.info("=" * 60)
        
        # Pages
        if self.crawl_stats['pages_parsed']:
            logger.info(f"✅ Parsed: {len(self.crawl_stats['pages_parsed'])} pages")
        
        if self.crawl_stats['pages_duplicated']:
            logger.info(f"🔄 Duplicates removed: {len(self.crawl_stats['pages_duplicated'])} pages")
        
        # Downloads
        total_downloads = len(self.crawl_stats['downloads_success'])
        total_failed = len(self.crawl_stats['downloads_failed'])
        total_skipped = len(self.crawl_stats['downloads_skipped'])
        
        if total_downloads > 0:
            logger.info(f"📥 Downloads successful: {total_downloads} files")
            # Show first 5 downloaded files with details
            if logger.isEnabledFor(logging.DEBUG):
                for item in self.crawl_stats['downloads_success'][:5]:
                    logger.debug(f"  ✅ {item}")
                if total_downloads > 5:
                    logger.debug(f"  ... and {total_downloads - 5} more")
            else:
                # In INFO mode, show compact list
                logger.info(f"   Files: {', '.join(self.crawl_stats['downloads_success'][:3])}")
                if total_downloads > 3:
                    logger.info(f"   ... and {total_downloads - 3} more (see downloads/ folder)")
        
        if total_skipped > 0:
            logger.info(f"⏭️ Downloads skipped: {total_skipped} files (size limit)")
            if logger.isEnabledFor(logging.DEBUG):
                for item in self.crawl_stats['downloads_skipped'][:3]:
                    logger.debug(f"  ⏭️ {item}")
        
        if total_failed > 0:
            logger.warning(f"❌ Downloads failed: {total_failed} files")
            if logger.isEnabledFor(logging.DEBUG):
                for item in self.crawl_stats['downloads_failed'][:3]:
                    logger.debug(f"  ❌ {item}")
        
        # Internal Links
        if self.crawl_stats['internal_links_created']:
            logger.info(f"🔗 Internal links created: {len(self.crawl_stats['internal_links_created'])} links")
        
        # CSS
        if self.crawl_stats['css_extracted']:
            logger.info(f"🎨 CSS files extracted: {len(self.crawl_stats['css_extracted'])} files")
        
        if self.crawl_stats['css_failed']:
            logger.warning(f"⚠️ CSS extraction failed: {len(self.crawl_stats['css_failed'])} files")
        
        logger.info("=" * 60)
        logger.info("")
