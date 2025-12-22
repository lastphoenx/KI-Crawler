import os
import time
import json
import logging
import asyncio
from pathlib import Path
from typing import Set, List, Dict, Optional
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import yaml

from navigation_strategy import (
    NavigationStrategy, 
    PCloudNavigationStrategy,
    GenericNavigationStrategy,
    GitHubNavigationStrategy
)
from rate_limiter import RateLimiter
from rendering_strategy import get_rendering_strategy, StaticRenderingStrategy, SPADetector
from sitemap_parser import SitemapParser
from openapi_detector import OpenAPIDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Crawler:
    """
    Web crawler with advanced URL scope control and depth tracking.
    
    URL SCOPE CONTROL (3-Option System):
    ==================================
    1. Strict Mode (strict_base_path=True): Only crawl URLs under entry URL's path
       Example: Entry=/docs/api/ → Only crawls /docs/api/*
    
    2. Parent Levels (parent_levels=N): Go N levels up from entry URL
       Example: Entry=/docs/api/, parent_levels=1 → Base=/docs/ → Crawls /docs/*
    
    3. Pattern Filters:
       - url_must_contain: List of patterns (OR logic) - URL must match at least one
       - url_must_not_contain: List of patterns (AND logic) - URL must match none
    
    DEPTH TRACKING (Click-Distance Based):
    ====================================
    - Depth = Click-distance from entry URL, NOT URL path depth
    - Example: Entry → Link1 → Link2 = depth 2
    - Example: /a/b/c/d/e.html can be depth 1 if linked directly from entry
    - Prevents infinite crawling even with circular links
    
    EDGE CASES HANDLED:
    ==================
    1. Circular Links: visited_urls Set prevents re-crawling same URL
    2. Empty Queue: Warns user if scope filters too restrictive (< 3 pages)
    3. Depth vs Path: Uses click-distance (url_depth dict), not URL structure
    """
    
    def __init__(self, config_path: str = "config.yaml", nav_strategy: NavigationStrategy = None, max_workers: int = 5):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.entry_url = self.config['crawler']['entry_url']
        self.max_retries = self.config['crawler']['max_retries']
        self.retry_backoff = self.config['crawler']['retry_backoff_factor']
        self.timeout = self.config['crawler']['timeout_seconds']
        self.user_agent = self.config['crawler']['user_agent']
        self.max_workers = max_workers
        self.max_pages = self.config['crawler'].get('max_pages', 200)
        
        # URL Scope Control (NEW)
        self.strict_base_path = self.config['crawler'].get('strict_base_path', True)
        self.parent_levels = self.config['crawler'].get('parent_levels', 0)
        self.url_must_contain = self.config['crawler'].get('url_must_contain', [])
        self.url_must_not_contain = self.config['crawler'].get('url_must_not_contain', [])
        self.base_path = self._extract_base_path(self.entry_url)
        
        self.cache_dir = Path(self.config['output']['cache_dir'])
        self.cache_dir.mkdir(exist_ok=True)
        
        self.visited_urls: Set[str] = set()
        self.to_crawl: List[str] = []
        self.errors: Dict[str, str] = {}
        self.pages: Dict[str, Dict] = {}
        self.detected_openapi: Optional[Dict] = None
        
        # Depth tracking for click-distance (NOT URL path depth)
        self.url_depth: Dict[str, int] = {}  # {url: click_distance_from_entry}
        self.crawl_depth_limit = self.config.get('crawler', {}).get('crawl_depth', 3)
        
        # Out-of-scope tracking for debugging
        self.out_of_scope_urls: Dict[str, int] = {}  # {url_prefix: count}
        
        # Strategy Factory: Select navigation strategy based on config
        NAV_STRATEGIES = {
            'pcloud': PCloudNavigationStrategy,
            'generic': GenericNavigationStrategy,
            'github': GitHubNavigationStrategy,
        }
        
        # Get strategy name from config (with fallback to 'pcloud')
        strategy_name = self.config.get('crawler', {}).get('nav_strategy', 'pcloud')
        if not strategy_name:
            strategy_name = 'pcloud'
        
        StrategyCls = NAV_STRATEGIES.get(strategy_name, PCloudNavigationStrategy)
        
        # Allow manual override via nav_strategy parameter
        self.nav_strategy = nav_strategy or StrategyCls(self.entry_url, config=self.config.get('crawler', {}))
        
        self.rate_limiter = RateLimiter(user_agent=self.user_agent)
        self.rendering_strategy = get_rendering_strategy(self.config)
        self.spa_detector = SPADetector()
        self.sitemap_parser = SitemapParser(user_agent=self.user_agent)
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Sitemap caching - fetch once, reuse everywhere
        self._sitemap_urls_cache = None
    
    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to prevent duplicates:
        - Remove fragments (#section)
        - Remove query parameters (?lang=de)
        - Normalize trailing slashes
        """
        parsed = urlparse(url)
        
        # Reconstruct URL without fragment and query
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Normalize trailing slashes: keep for directories, remove for files
        if normalized.endswith('/'):
            # Already has trailing slash (directory)
            pass
        elif '.' in normalized.split('/')[-1]:
            # Has file extension (file) - no trailing slash
            pass
        else:
            # No extension, likely directory - add trailing slash
            normalized += '/'
        
        return normalized
    
    def _extract_base_path(self, url: str) -> str:
        """Extract base path from entry URL for strict mode"""
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        
        # Check if last segment is a file (has extension)
        last_segment = path.split('/')[-1]
        if '.' in last_segment:
            # Has extension → remove extension but KEEP filename as directory
            # Example: /projektmanagement/module.html → /projektmanagement/module/
            # This treats the entry page's name (without extension) as the scope
            filename_without_ext = last_segment.rsplit('.', 1)[0]
            path_parts = path.split('/')[:-1]  # Remove last segment
            path_parts.append(filename_without_ext)  # Add back without extension
            path = '/'.join(path_parts)
        
        # THEN go up N levels if parent_levels > 0
        if self.parent_levels > 0:
            parts = [p for p in path.split('/') if p]
            if len(parts) >= self.parent_levels:
                parts = parts[:-self.parent_levels]
            else:
                # Edge case: URL too short, fallback to root
                parts = []
            path = '/' + '/'.join(parts)
        
        base = f"{parsed.scheme}://{parsed.netloc}{path}/"
        logger.info(f"🎯 Base path for filtering: {base} (parent_levels={self.parent_levels})")
        return base
    
    def _get_sitemap_urls(self) -> Set[str]:
        """Get sitemap URLs with caching - fetch once, reuse everywhere"""
        if self._sitemap_urls_cache is None:
            self._sitemap_urls_cache = self.sitemap_parser.fetch_sitemaps(self.entry_url)
        return self._sitemap_urls_cache
    
    def _is_within_scope(self, url: str) -> bool:
        """Check if URL is within crawling scope (NEW filter logic)"""
        # 1. Strict Base Path Mode (takes priority)
        if self.strict_base_path:
            # Check base path OR sub-directory scopes (if expanded)
            in_scope = url.startswith(self.base_path)
            if not in_scope and hasattr(self, 'sub_directory_scopes'):
                in_scope = any(url.startswith(sd) for sd in self.sub_directory_scopes)
            
            if not in_scope:
                # Track out-of-scope URLs
                self._track_out_of_scope_url(url)
                logger.debug(f"⊘ Blocked (not under base path): {url}")
                return False
        # 2. Parent Levels Mode (only if strict disabled)
        elif self.parent_levels > 0:
            # Check base path OR sub-directory scopes
            in_scope = url.startswith(self.base_path)
            if not in_scope and hasattr(self, 'sub_directory_scopes'):
                in_scope = any(url.startswith(sd) for sd in self.sub_directory_scopes)
            
            if not in_scope:
                self._track_out_of_scope_url(url)
                logger.debug(f"⊘ Blocked (outside parent scope): {url}")
                return False
        # If neither: no base-path filtering (global crawl within domain)
        
        # 3. Must Contain Patterns (OR logic)
        if self.url_must_contain:
            if not any(pattern in url for pattern in self.url_must_contain):
                self._track_out_of_scope_url(url)
                logger.debug(f"⊘ Blocked (missing required pattern): {url}")
                return False
        
        # 4. Must NOT Contain Patterns (AND logic)
        if self.url_must_not_contain:
            if any(pattern in url for pattern in self.url_must_not_contain):
                self._track_out_of_scope_url(url)
                logger.debug(f"⊘ Blocked (contains excluded pattern): {url}")
                return False
        
        return True
    
    def _track_out_of_scope_url(self, url: str):
        """Track out-of-scope URLs for summary reporting"""
        # Extract path prefix (up to 3 levels deep for grouping)
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # Create prefix from first 3 path segments
        prefix_parts = path_parts[:3] if len(path_parts) >= 3 else path_parts
        prefix = f"{parsed.scheme}://{parsed.netloc}/" + '/'.join(prefix_parts) + '/'
        
        self.out_of_scope_urls[prefix] = self.out_of_scope_urls.get(prefix, 0) + 1
    
    def _log_out_of_scope_summary(self):
        """Log summary of out-of-scope URLs found during crawl"""
        if not self.out_of_scope_urls:
            return
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 OUT-OF-SCOPE LINKS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Found {sum(self.out_of_scope_urls.values())} out-of-scope links")
        logger.info("")
        
        # Sort by count (descending)
        sorted_urls = sorted(self.out_of_scope_urls.items(), key=lambda x: x[1], reverse=True)
        
        # Show top 15
        for url_prefix, count in sorted_urls[:15]:
            logger.info(f"  {count:>3}x  {url_prefix}")
        
        if len(sorted_urls) > 15:
            remaining = len(sorted_urls) - 15
            remaining_count = sum(count for _, count in sorted_urls[15:])
            logger.info(f"  ... and {remaining} more prefixes ({remaining_count} total links)")
        
        logger.info("=" * 60)
        logger.info("")
    
    def _check_depth_limit(self, url: str, parent_url: str = None) -> bool:
        """Check if URL exceeds crawl depth limit (click-distance based)"""
        # If no parent, it's the entry URL (depth 0)
        if parent_url is None:
            self.url_depth[url] = 0
            return True
        
        # Calculate depth from parent
        parent_depth = self.url_depth.get(parent_url, 0)
        current_depth = parent_depth + 1
        
        if current_depth > self.crawl_depth_limit:
            logger.debug(f"⊘ Blocked (depth {current_depth} > limit {self.crawl_depth_limit}): {url}")
            return False
        
        self.url_depth[url] = current_depth
        return True
    
    def _check_crawl_queue_fallback(self):
        """
        Warn user if scope filters are too restrictive and result in very few pages.
        Suggests relaxing filters if queue size is suspiciously small.
        """
        queue_size = len(self.to_crawl) + len(self.visited_urls)
        
        # Dynamic threshold: at least 5% of max_pages, minimum 3
        threshold = max(3, self.max_pages // 20)
        
        # If queue is very small and strict mode is enabled, warn user
        if queue_size < threshold:
            logger.warning("⚠️ URL Scope Control Warning:")
            logger.warning(f"   Only {queue_size} page(s) found with current filters (expected at least {threshold})")
            
            crawler_config = self.config.get('crawler', {})
            
            if crawler_config.get('strict_base_path', True):
                logger.warning("   💡 Suggestion 1: Set strict_base_path=False to allow sibling paths")
            
            current_parent_levels = crawler_config.get('parent_levels', 0)
            if current_parent_levels < 2:
                logger.warning(f"   💡 Suggestion 2: Increase parent_levels from {current_parent_levels} to {current_parent_levels + 1}")
            
            if crawler_config.get('url_must_contain'):
                patterns = crawler_config['url_must_contain']
                logger.warning(f"   💡 Suggestion 3: Review url_must_contain filters: {patterns}")
            
            if crawler_config.get('url_must_not_contain'):
                patterns = crawler_config['url_must_not_contain']
                logger.warning(f"   💡 Suggestion 4: Review url_must_not_contain filters: {patterns}")
            
            logger.warning("   📝 Adjust these settings in Template or New Crawl config")
    
    def _is_valid_url(self, url: str, parent_url: str = None) -> bool:
        # Normalize URL to prevent duplicates (trailing slash, query params, fragments)
        normalized_url = self._normalize_url(url)
        
        # Also normalize parent_url if provided for consistent depth tracking
        normalized_parent = self._normalize_url(parent_url) if parent_url else None
        
        if normalized_url in self.visited_urls:
            return False
        if not normalized_url.startswith(('http://', 'https://')):
            return False
        if self._get_domain(normalized_url) != self._get_domain(self.entry_url):
            return False
        if any(normalized_url.endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.zip']):
            return False
        
        # Check depth limit (click-distance based) - CRITICAL: use keyword argument!
        if not self._check_depth_limit(normalized_url, parent_url=normalized_parent):
            return False
        
        # Check scope filters - use normalized URL
        if not self._is_within_scope(normalized_url):
            return False
        
        return True
    
    def _fetch_url_lightweight(self, url: str, timeout: int = 5) -> Optional[str]:
        """Lightweight fetch for preflight scan - no JS rendering, shorter timeout"""
        if not self.rate_limiter.can_fetch(url):
            return None
        
        self.rate_limiter.wait_if_needed(url)
        
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.debug(f"Lightweight fetch failed for {url}: {e}")
            return None
    
    def _fetch_url(self, url: str) -> Optional[str]:
        if not self.rate_limiter.can_fetch(url):
            logger.warning(f"Blocked by robots.txt: {url}")
            self.errors[url] = "Blocked by robots.txt"
            return None
        
        self.rate_limiter.wait_if_needed(url)
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Fetching ({attempt}/{self.max_retries}): {url}")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                html = response.text
                
                if not isinstance(self.rendering_strategy, StaticRenderingStrategy):
                    is_spa = asyncio.run(self.spa_detector.is_spa(url, html))
                    if is_spa:
                        logger.info(f"📱 SPA detected. Re-rendering with JS: {url}")
                        try:
                            rendered_html = asyncio.run(self.rendering_strategy.render(url))
                            if rendered_html is not None:
                                html = rendered_html
                            else:
                                logger.warning("JS rendering failed, using static HTML")
                        except Exception as e:
                            logger.warning(f"JS rendering error: {e}. Using static HTML")
                
                return html
            except requests.RequestException as e:
                wait_time = (self.retry_backoff ** (attempt - 1))
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {self.max_retries} attempts: {url} - {e}")
                    self.errors[url] = str(e)
                    return None
        return None
    
    def _cache_html(self, url: str, html: str):
        """Cache HTML with URL mapping for re-parsing"""
        url_hash = abs(hash(url)) % 10000000
        cache_file = self.cache_dir / f"{url_hash}.html"
        
        # Save HTML
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Save URL mapping
        mapping_file = self.cache_dir / f"{url_hash}.url"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            f.write(url)
        
        # Save metadata
        metadata_file = self.cache_dir / f"{url_hash}.meta"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            import json
            from datetime import datetime
            json.dump({
                'url': url,
                'cached_at': datetime.now().isoformat(),
                'html_size': len(html)
            }, f, indent=2)
        
        logger.debug(f"Cached: {url} → {cache_file.name}")
        return cache_file
    
    def load_from_cache(self) -> Dict[str, Dict]:
        """Load all cached pages for re-parsing (Snapshot first, parse later)"""
        logger.info(f"Loading cached pages from {self.cache_dir}")
        pages = {}
        
        for html_file in self.cache_dir.glob("*.html"):
            url_file = html_file.with_suffix('.url')
            
            if url_file.exists():
                with open(url_file, 'r', encoding='utf-8') as f:
                    url = f.read().strip()
                
                with open(html_file, 'r', encoding='utf-8') as f:
                    html = f.read()
                
                pages[url] = {'raw_html': html}
                logger.debug(f"Loaded from cache: {url}")
        
        logger.info(f"✓ Loaded {len(pages)} pages from cache")
        return pages

    
    def _build_crawl_queue(self):
        logger.info(f"Building crawl queue from {self.entry_url}")
        
        # Normalize entry URL to prevent duplicates
        normalized_entry = self._normalize_url(self.entry_url)
        
        html = self._fetch_url(self.entry_url)
        if html is None:
            logger.error("Failed to fetch entry URL")
            return
        
        self._cache_html(self.entry_url, html)
        # CONSISTENCY: Use normalized URL as key, store original for HTTP requests
        self.pages[normalized_entry] = {
            'raw_html': html,
            'original_url': self.entry_url  # Keep for fetching/caching
        }
        self.visited_urls.add(normalized_entry)
        
        # Initialize depth tracking: entry URL is at depth 0 (click-distance based)
        self.url_depth[normalized_entry] = 0
        
        sitemap_urls = self._get_sitemap_urls()
        if sitemap_urls:
            logger.info(f"📑 Sitemap found: {len(sitemap_urls)} URLs")
            for url in sitemap_urls:
                # Pass entry_url as parent for depth tracking
                if self._is_valid_url(url, parent_url=normalized_entry):
                    classification, absolute_url = self.nav_strategy.classify_link(url, self.entry_url)
                    normalized_absolute = self._normalize_url(absolute_url)
                    if classification == 'method' and normalized_absolute not in self.to_crawl:
                        self.to_crawl.append(normalized_absolute)
        else:
            logger.info("No sitemap found, using navigation strategy")
            nav_links = self.nav_strategy.extract_nav_links(html)
            logger.info(f"Found {len(nav_links)} top-level navigation links")
            
            # For GitHub strategy: nav_links are direct file URLs, not categories to scan
            if isinstance(self.nav_strategy, GitHubNavigationStrategy):
                # Add all GitHub raw URLs directly to crawl queue (they're files, not categories)
                for url in nav_links:
                    normalized_url = self._normalize_url(url)
                    # GitHub files are one click away from entry (depth 1)
                    if self._is_valid_url(url, parent_url=normalized_entry) and normalized_url not in self.visited_urls and normalized_url not in self.to_crawl:
                        self.to_crawl.append(normalized_url)
                # Skip category scanning for GitHub
                logger.info(f"Added {len(nav_links)} GitHub files directly to crawl queue")
            else:
                # For other strategies: scan categories as usual
                categories_to_scan = nav_links.copy()
            
                # Add max_pages protection to prevent exponential queue growth
                while categories_to_scan and len(self.to_crawl) < self.max_pages:
                    nav_url = categories_to_scan.pop(0)
                    normalized_nav = self._normalize_url(nav_url)
                    
                    if normalized_nav in self.visited_urls:
                        continue
                    
                    # Category pages are one click away from entry (depth 1)
                    if not self._check_depth_limit(normalized_nav, parent_url=normalized_entry):
                        continue
                    
                    logger.info(f"Scanning category: {nav_url}")
                    cat_html = self._fetch_url(nav_url)
                    
                    if cat_html is None:
                        continue
                    
                    self._cache_html(nav_url, cat_html)
                    # CONSISTENCY: Use normalized URL as key
                    self.pages[normalized_nav] = {
                        'raw_html': cat_html,
                        'original_url': nav_url
                    }
                    self.visited_urls.add(normalized_nav)
                    
                    submenu_links = self.nav_strategy.extract_submenu_links(cat_html, nav_url)
                    for link in submenu_links:
                        classification, absolute_url = self.nav_strategy.classify_link(link, nav_url)
                        normalized_absolute = self._normalize_url(absolute_url)
                        
                        if classification == 'method':
                            # Method pages inherit depth from category (nav_url is parent)
                            if self._is_valid_url(absolute_url, parent_url=normalized_nav) and normalized_absolute not in self.visited_urls and normalized_absolute not in self.to_crawl:
                                self.to_crawl.append(normalized_absolute)
                        elif classification == 'category':
                            # Subcategories inherit depth from parent category
                            if self._is_valid_url(absolute_url, parent_url=normalized_nav) and normalized_absolute not in self.visited_urls and normalized_absolute not in categories_to_scan:
                                categories_to_scan.append(normalized_absolute)
        
        # Log final queue status for debugging
        logger.info(f"✅ Queue built: {len(self.to_crawl)} pages ready to crawl")
        logger.info(f"   Visited (categories): {len(self.visited_urls)}")
        logger.info(f"   Total discovered: {len(self.to_crawl) + len(self.visited_urls)}")
        
        # Check if scope filters are too restrictive
        self._check_crawl_queue_fallback()
    
    def _preflight_scan(self) -> int:
        """
        Dry-run scan to count all pages (categories + details) without fetching content.
        Returns total number of pages that will be crawled.
        """
        category_count = 0
        detail_count = 0
        
        # Get initial HTML with lightweight fetch
        entry_html = self._fetch_url_lightweight(self.entry_url)
        if entry_html is None:
            logger.warning("Could not fetch entry URL for preflight scan")
            return 0
        
        # Try sitemap first (cached)
        sitemap_urls = self._get_sitemap_urls()
        
        if sitemap_urls:
            # Count sitemap URLs (with scope filtering!)
            for url in sitemap_urls:
                normalized_url = self._normalize_url(url)
                
                # CRITICAL: Check if URL is within scope before counting
                if not self._is_within_scope(normalized_url):
                    continue
                
                classification, _ = self.nav_strategy.classify_link(url, self.entry_url)
                if classification == 'method':
                    detail_count += 1
            
            # FALLBACK: If no URLs found, look for sub-directories instead of going up
            if detail_count == 0 and self.base_path.count('/') > 3:
                logger.warning(f"⚠️ No pages found directly under {self.base_path}")
                logger.warning(f"   🔍 Strategy: Looking for sub-directories (DOWN) instead of going up...")
                
                # Find all sub-directories that contain pages
                # Example: /de/Studium/ → find /de/Studium/Vor-dem-Studium/, /de/Studium/Im-Studium/
                sub_dirs = set()
                for url in sitemap_urls:
                    if url.startswith(self.base_path):
                        # Extract first sub-directory level
                        remainder = url[len(self.base_path):].lstrip('/')
                        if '/' in remainder:
                            first_dir = remainder.split('/')[0]
                            sub_dir = self.base_path.rstrip('/') + '/' + first_dir + '/'
                            sub_dirs.add(sub_dir)
                
                if sub_dirs:
                    logger.info(f"   📂 Found {len(sub_dirs)} sub-directories with content:")
                    for sd in sorted(sub_dirs)[:5]:
                        logger.info(f"      • {sd}")
                    if len(sub_dirs) > 5:
                        logger.info(f"      ... and {len(sub_dirs) - 5} more")
                    
                    # Expand scope to include ALL sub-directories
                    self.sub_directory_scopes = list(sub_dirs)
                    
                    # Rescan with expanded scope
                    detail_count = 0
                    for url in sitemap_urls:
                        normalized_url = self._normalize_url(url)
                        # Check if URL is under ANY sub-directory
                        if any(normalized_url.startswith(sd) for sd in self.sub_directory_scopes):
                            classification, _ = self.nav_strategy.classify_link(url, self.entry_url)
                            if classification == 'method':
                                detail_count += 1
                    
                    logger.info(f"   ✅ Found {detail_count} pages across {len(sub_dirs)} sub-directories")
                else:
                    # No sub-directories found → fallback to going UP (old behavior)
                    logger.warning(f"   No sub-directories found. Trying one level up...")
                    path_parts = [p for p in self.base_path.rstrip('/').split('/') if p]
                    if len(path_parts) > 2:
                        path_parts = path_parts[:-1]
                        parsed = urlparse(self.base_path)
                        fallback_base = f"{parsed.scheme}://{parsed.netloc}/" + '/'.join(path_parts[2:]) + '/'
                        logger.info(f"   🔄 Fallback base path: {fallback_base}")
                        self.base_path = fallback_base
                        
                        # Rescan
                        detail_count = 0
                        for url in sitemap_urls:
                            normalized_url = self._normalize_url(url)
                            if not self._is_within_scope(normalized_url):
                                continue
                            classification, _ = self.nav_strategy.classify_link(url, self.entry_url)
                            if classification == 'method':
                                detail_count += 1
            
            logger.info(f"Preflight: Sitemap contains {detail_count} detail pages (scope-filtered)")
            return detail_count
        
        # No sitemap - scan navigation structure
        nav_links = self.nav_strategy.extract_nav_links(entry_html)
        
        if isinstance(self.nav_strategy, GitHubNavigationStrategy):
            # GitHub strategy: all nav_links are files
            detail_count = len(nav_links)
            logger.info(f"Preflight: Found {detail_count} GitHub files")
            return detail_count
        
        # For other strategies: traverse category tree (with max_pages limit)
        categories_to_scan = nav_links.copy()
        scanned_categories = set()
        
        # Initialize depth tracking for preflight (consistency with _build_crawl_queue)
        preflight_depth = {self.entry_url: 0}
        
        while categories_to_scan and (category_count + detail_count) < self.max_pages:
            nav_url = categories_to_scan.pop(0)
            
            if nav_url in scanned_categories:
                continue
            
            # Check depth limit (consistency with _build_crawl_queue)
            parent_depth = preflight_depth.get(self.entry_url, 0)
            current_depth = parent_depth + 1
            if current_depth > self.crawl_depth_limit:
                continue
            preflight_depth[nav_url] = current_depth
            
            # Check scope (consistency with _build_crawl_queue)
            if not self._is_within_scope(nav_url):
                continue
            
            scanned_categories.add(nav_url)
            category_count += 1
            
            # Fetch category page with lightweight method and short timeout
            cat_html = self._fetch_url_lightweight(nav_url, timeout=5)
            if cat_html is None:
                continue
            
            # Extract links from category
            submenu_links = self.nav_strategy.extract_submenu_links(cat_html, nav_url)
            for link in submenu_links:
                classification, absolute_url = self.nav_strategy.classify_link(link, nav_url)
                
                if classification == 'method':
                    # Check depth and scope for method pages too
                    method_depth = current_depth + 1
                    if method_depth <= self.crawl_depth_limit and self._is_within_scope(absolute_url):
                        detail_count += 1
                elif classification == 'category':
                    if absolute_url not in scanned_categories and absolute_url not in categories_to_scan:
                        # Store depth for subcategories
                        preflight_depth[absolute_url] = current_depth + 1
                        categories_to_scan.append(absolute_url)
        
        total = category_count + detail_count
        logger.info(f"Preflight: {total} total pages ({category_count} categories + {detail_count} details)")
        return total
    
    def _fetch_and_cache(self, url: str) -> Optional[str]:
        """Worker function for parallel fetching."""
        normalized_url = self._normalize_url(url)
        
        if normalized_url in self.visited_urls:
            return None
        
        self.visited_urls.add(normalized_url)
        
        html = self._fetch_url(url)
        if html is None:
            return None
        
        self._cache_html(url, html)
        # CONSISTENCY: Use normalized URL as key
        self.pages[normalized_url] = {
            'raw_html': html,
            'original_url': url
        }
        
        if not self.detected_openapi:
            openapi_info = OpenAPIDetector.detect_openapi(html, url)
            if openapi_info:
                self.detected_openapi = openapi_info
                logger.info(f"🔍 OpenAPI detected: {openapi_info['type']} (v{openapi_info['version']})")
                if 'url' in openapi_info:
                    logger.info(f"   Spec URL: {openapi_info['url']}")
        
        return html
    
    def crawl(self):
        logger.info("="*60)
        logger.info("PREFLIGHT SCAN - Counting all pages...")
        logger.info("="*60)
        
        # Do a dry-run to count all pages (categories + details)
        total_pages_count = self._preflight_scan()
        logger.info(f"📊 Preflight complete: Found {total_pages_count} total pages to crawl")
        
        logger.info("="*60)
        logger.info("BUILDING CRAWL QUEUE")
        logger.info("="*60)
        
        self._build_crawl_queue()
        
        # ENFORCE MAX PAGES LIMIT
        if len(self.to_crawl) > self.max_pages:
            logger.warning(f"Queue has {len(self.to_crawl)} pages, limiting to max_pages={self.max_pages}")
            self.to_crawl = self.to_crawl[:self.max_pages]
        
        logger.info(f"Queue has {len(self.to_crawl)} detailed pages to crawl")
        logger.info("="*60)
        logger.info("CRAWLING DETAIL PAGES (parallel with {0} workers)".format(self.max_workers))
        logger.info("="*60)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._fetch_and_cache, url): url for url in self.to_crawl}
            
            completed = 0
            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    if result:
                        completed += 1
                        logger.info(f"✓ Fetched: {url}")
                except Exception as e:
                    logger.error(f"✗ Error fetching {url}: {e}")
                    self.errors[url] = str(e)
            
            logger.info(f"Parallel crawl: {completed}/{len(self.to_crawl)} pages fetched")
        
        logger.info(f"Crawl complete. Visited {len(self.visited_urls)} pages. Errors: {len(self.errors)}")
        
        # Log out-of-scope summary
        self._log_out_of_scope_summary()
        
        return self.pages, self.errors


if __name__ == "__main__":
    crawler = Crawler()
    pages, errors = crawler.crawl()
    
    print(f"\n✓ Crawled {len(pages)} pages")
    print(f"✗ Errors: {len(errors)}")
    
    if errors:
        print("\nFailed URLs:")
        for url, error in errors.items():
            print(f"  - {url}: {error}")
