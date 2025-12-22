from abc import ABC, abstractmethod
from typing import List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

__all__ = [
    'NavigationStrategy',
    'PCloudNavigationStrategy',
    'GitHubDocsNavigationStrategy',
    'ReadTheDocsNavigationStrategy',
    'GenericNavigationStrategy',
    'GitHubNavigationStrategy'
]


class NavigationStrategy(ABC):
    """Abstract base class for platform-specific navigation extraction."""
    
    def __init__(self, base_url: str, config=None):
        self.base_url = base_url
        self.entry_url = base_url
        self.config = config
    
    @abstractmethod
    def extract_nav_links(self, html: str) -> List[str]:
        """Extract top-level navigation links from homepage."""
        pass
    
    @abstractmethod
    def extract_submenu_links(self, html: str, page_url: str) -> List[str]:
        """Extract links from a category/submenu page."""
        pass
    
    @abstractmethod
    def classify_link(self, href: str, source_url: str) -> Tuple[str, str]:
        """
        Classify a link as 'method', 'category', or 'ignore'.
        Returns: (classification, absolute_url)
        """
        pass


class PCloudNavigationStrategy(NavigationStrategy):
    """Navigation strategy for pCloud API documentation."""
    
    def extract_nav_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        nav_div = soup.find('div', class_='docs-nav')
        if nav_div:
            for a in nav_div.find_all('a', href=True):
                href = a['href']
                if href and not href.startswith('#'):
                    absolute_url = urljoin(self.base_url, href)
                    if absolute_url not in seen:
                        seen.add(absolute_url)
                        links.append(absolute_url)
        
        return links
    
    def extract_submenu_links(self, html: str, page_url: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        dev_content = soup.find('div', class_='dev-content')
        if dev_content:
            for a in dev_content.find_all('a', href=True):
                href = a['href']
                if href and not href.startswith('#'):
                    absolute_url = urljoin(page_url, href)
                    if absolute_url not in seen:
                        seen.add(absolute_url)
                        links.append(absolute_url)
        
        return links
    
    def classify_link(self, href: str, source_url: str) -> Tuple[str, str]:
        if not href or href.startswith('#'):
            return ('ignore', '')
        
        absolute_url = urljoin(source_url, href)
        
        if href.endswith('.html'):
            return ('method', absolute_url)
        elif href.endswith('/'):
            return ('category', absolute_url)
        
        return ('ignore', absolute_url)


class GitHubDocsNavigationStrategy(NavigationStrategy):
    """Navigation strategy for GitHub Docs."""
    
    def extract_nav_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        nav = soup.find('nav', class_='sidebar-nav')
        if nav:
            for a in nav.find_all('a', href=True):
                href = a['href']
                if href and not href.startswith('#'):
                    absolute_url = urljoin(self.base_url, href)
                    if absolute_url not in seen:
                        seen.add(absolute_url)
                        links.append(absolute_url)
        
        return links
    
    def extract_submenu_links(self, html: str, page_url: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        article = soup.find('article', class_='markdown-body')
        if article:
            for a in article.find_all('a', href=True):
                href = a['href']
                if href and not href.startswith('#'):
                    absolute_url = urljoin(page_url, href)
                    if absolute_url not in seen:
                        seen.add(absolute_url)
                        links.append(absolute_url)
        
        return links
    
    def classify_link(self, href: str, source_url: str) -> Tuple[str, str]:
        if not href or href.startswith('#'):
            return ('ignore', '')
        
        absolute_url = urljoin(source_url, href)
        
        if '/docs/' in href or '/docs/' in absolute_url:
            if href.endswith('.md') or not any(href.endswith(ext) for ext in ['.pdf', '.png', '.jpg']):
                return ('method', absolute_url)
        
        if href.endswith('/') and '/docs/' in absolute_url:
            return ('category', absolute_url)
        
        return ('ignore', absolute_url)


class ReadTheDocsNavigationStrategy(NavigationStrategy):
    """Navigation strategy for ReadTheDocs-style documentation."""
    
    def extract_nav_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        nav = soup.find('div', class_='toctree-wrapper') or soup.find('nav', class_='wy-nav-side')
        if nav:
            for a in nav.find_all('a', href=True):
                href = a['href']
                if href and not href.startswith('#') and not href.startswith('javascript'):
                    absolute_url = urljoin(self.base_url, href)
                    if absolute_url not in seen:
                        seen.add(absolute_url)
                        links.append(absolute_url)
        
        return links
    
    def extract_submenu_links(self, html: str, page_url: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        content = soup.find('div', class_='document') or soup.find('main')
        if content:
            for a in content.find_all('a', href=True):
                href = a['href']
                if href and not href.startswith('#') and not href.startswith('javascript'):
                    absolute_url = urljoin(page_url, href)
                    if absolute_url not in seen:
                        seen.add(absolute_url)
                        links.append(absolute_url)
        
        return links
    
    def classify_link(self, href: str, source_url: str) -> Tuple[str, str]:
        if not href or href.startswith('#') or href.startswith('javascript'):
            return ('ignore', '')
        
        absolute_url = urljoin(source_url, href)
        
        if href.endswith('.html') or absolute_url.endswith('.html'):
            return ('method', absolute_url)
        elif href.endswith('/'):
            return ('category', absolute_url)
        
        return ('ignore', absolute_url)


class GenericNavigationStrategy(NavigationStrategy):
    """
    Generic navigation strategy that collects links from nav/main/body.
    Domain-locked with include/exclude pattern filtering.
    """
    
    def extract_nav_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        links = []
        
        from urllib.parse import urlparse
        import re
        
        def strip_fragment(url: str) -> str:
            return url.split('#', 1)[0]
        
        def same_netloc(a: str, b: str) -> bool:
            return urlparse(a).netloc.lower() == urlparse(b).netloc.lower()
        
        def matches_any(patterns: List[str], text: str) -> bool:
            return any(re.search(p, text) for p in patterns or [])
        
        base = self.base_url
        include_patterns = getattr(self.config, 'include_patterns', []) if self.config else []
        exclude_patterns = getattr(self.config, 'exclude_patterns', []) if self.config else []
        max_pages = getattr(self.config, 'max_pages', 200) if self.config else 200
        
        def consider(href: str):
            if not href or href.startswith('#'):
                return
            if href.startswith(('javascript:', 'mailto:')):
                return
            
            abs_url = strip_fragment(urljoin(base, href))
            
            # Domain lock
            if not same_netloc(abs_url, base):
                return
            
            # Exclude patterns
            if exclude_patterns and matches_any(exclude_patterns, abs_url):
                return
            
            # Include patterns (optional)
            if include_patterns and not matches_any(include_patterns, abs_url):
                return
            
            if abs_url not in seen:
                seen.add(abs_url)
                links.append(abs_url)
        
        # First: targeted containers
        for container in soup.find_all(['nav', 'main']):
            for a in container.find_all('a', href=True):
                consider(a.get('href'))
        
        # Fallback: all links
        if not links:
            for a in soup.find_all('a', href=True):
                consider(a.get('href'))
        
        return links[:max_pages]
    
    def extract_submenu_links(self, html: str, page_url: str) -> List[str]:
        # Reuse extract_nav_links logic
        return self.extract_nav_links(html)
    
    def classify_link(self, href: str, source_url: str) -> Tuple[str, str]:
        if not href or href.startswith('#'):
            return ('ignore', '')
        
        absolute_url = urljoin(source_url, href)
        
        # Simple classification: if it's on same domain, it's a method page
        from urllib.parse import urlparse
        if urlparse(absolute_url).netloc == urlparse(source_url).netloc:
            return ('method', absolute_url)
        
        return ('ignore', absolute_url)


class GitHubNavigationStrategy(NavigationStrategy):
    """
    GitHub-specific strategy using GitHub API to fetch repository files.
    Builds raw.githubusercontent.com URLs for actual file content.
    """
    
    API = "https://api.github.com"
    
    def __init__(self, entry_url: str, config=None):
        super().__init__(entry_url, config=config)
        import requests
        import os
        from urllib.parse import urlparse
        
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'doc-crawler/1.0',
        })
        
        token = (getattr(config, 'github_token', None) if config else None) or os.getenv('GITHUB_TOKEN')
        if token:
            self.session.headers['Authorization'] = f'Bearer {token}'
        
        self.owner, self.repo = self._parse_owner_repo(entry_url)
    
    def _parse_owner_repo(self, url: str):
        from urllib.parse import urlparse
        p = urlparse(url)
        parts = [x for x in p.path.split('/') if x]
        if len(parts) < 2:
            raise ValueError(f"GitHub URL not in format owner/repo: {url}")
        return parts[0], parts[1]
    
    def _get_default_branch(self) -> str:
        try:
            r = self.session.get(f"{self.API}/repos/{self.owner}/{self.repo}", timeout=20)
            r.raise_for_status()
            return r.json().get('default_branch', 'main')
        except Exception as e:
            logger.warning(f"Could not fetch default branch: {e}")
            return 'main'
    
    def _get_tree_paths(self, branch: str) -> List[str]:
        try:
            r = self.session.get(
                f"{self.API}/repos/{self.owner}/{self.repo}/git/trees/{branch}",
                params={'recursive': '1'},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            tree = data.get('tree', [])
            paths = [item['path'] for item in tree if item.get('type') == 'blob' and item.get('path')]
            return paths
        except Exception as e:
            logger.error(f"Could not fetch repository tree: {e}")
            return []
    
    def extract_nav_links(self, html: str) -> List[str]:
        exts = getattr(self.config, 'github_extensions', None) if self.config else None
        exts = exts or ['.md', '.txt', '.py', '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.sh']
        
        max_pages = getattr(self.config, 'max_pages', 200) if self.config else 200
        github_max_files = getattr(self.config, 'github_max_files', 300) if self.config else 300
        cap = min(max_pages, github_max_files)
        
        branch = self._get_default_branch()
        paths = self._get_tree_paths(branch)
        
        def allowed(path: str) -> bool:
            lp = path.lower()
            return any(lp.endswith(e) for e in exts)
        
        # Build raw URLs
        raw_base = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/{branch}/"
        out = [raw_base + p for p in paths if allowed(p)]
        
        logger.info(f"Found {len(out)} files in GitHub repository")
        return out[:cap]
    
    def extract_submenu_links(self, html: str, page_url: str) -> List[str]:
        # GitHub strategy returns empty - raw files have no sublinks to extract
        return []
    
    def classify_link(self, href: str, source_url: str) -> Tuple[str, str]:
        # All links from GitHub API are method pages
        if href:
            return ('method', href)
        return ('ignore', '')
