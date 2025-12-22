"""
Crawl configuration model
"""

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass
class CrawlConfig:
    """Configuration for a crawl job"""
    
    # Basic settings
    url: str = ''
    output_name: str = 'documentation.docx'
    max_pages: int = 100
    crawl_depth: int = 2
    
    # Strategy settings
    strategy: str = 'auto'  # auto, sitemap, css, follow_all
    css_selectors: List[str] = field(default_factory=list)
    
    # Advanced settings
    parallel: bool = True
    workers: int = 5
    include_images: bool = True
    include_code: bool = True
    respect_robots: bool = True
    
    # URL filters
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    
    # URL Scope Control (NEW - prevents scope creep)
    strict_base_path: bool = True  # Only crawl URLs under start URL's path
    parent_levels: int = 0  # How many levels up from start URL (0=strict)
    url_must_contain: List[str] = field(default_factory=list)  # URLs must contain these strings
    url_must_not_contain: List[str] = field(default_factory=list)  # URLs must NOT contain these
    
    # Special features
    js_rendering: bool = False
    check_openapi: bool = False
    
    # HTML output formatting
    enhanced_html_formatting: bool = False
    extra_css_urls: List[str] = field(default_factory=list)
    use_fallback_css: bool = False
    inline_standalone: bool = False  # Generate standalone HTML with inlined assets
    
    # Content filtering
    min_content_length: int = 20  # Minimum text length to keep page (0=disable filtering)
    
    # Navigation strategy
    nav_strategy: str = 'pcloud'  # pcloud, generic, github
    
    # GitHub-specific options
    github_token: Optional[str] = None
    github_extensions: List[str] = field(default_factory=lambda: [
        '.md', '.txt', '.py', '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.sh', '.js', '.ts'
    ])
    github_max_files: int = 300
    
    # Template info
    template_id: str = 'custom'
    
    # Internal
    crawl_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def load_from_template(self, template: dict):
        """Load configuration from a template"""
        config = template.get('config', {})
        
        # Basic settings
        self.url = config.get('entry_url', config.get('url', self.url))
        self.output_name = config.get('output_name', self.output_name)
        self.strategy = config.get('strategy', self.strategy)
        self.css_selectors = config.get('css_selectors', [])
        self.max_pages = config.get('max_pages', self.max_pages)
        self.crawl_depth = config.get('crawl_depth', self.crawl_depth)
        self.parallel = config.get('parallel', self.parallel)
        self.workers = config.get('workers', self.workers)
        
        # URL Filters
        self.include_patterns = config.get('include_patterns', [])
        self.exclude_patterns = config.get('exclude_patterns', [])
        
        # URL Scope Control
        self.strict_base_path = config.get('strict_base_path', self.strict_base_path)
        self.parent_levels = config.get('parent_levels', self.parent_levels)
        self.url_must_contain = config.get('url_must_contain', [])
        self.url_must_not_contain = config.get('url_must_not_contain', [])
        
        # Navigation strategy
        self.nav_strategy = config.get('nav_strategy', self.nav_strategy)
        self.check_openapi = config.get('check_openapi', False)
        
        # GitHub settings
        self.github_token = config.get('github_token', self.github_token)
        self.github_extensions = config.get('github_extensions', self.github_extensions)
        self.github_max_files = config.get('github_max_files', self.github_max_files)
        
        # Document settings (may be nested)
        doc_config = config.get('document', {})
        if doc_config:
            self.enhanced_html_formatting = doc_config.get('enhanced_html_formatting', self.enhanced_html_formatting)
            self.use_fallback_css = doc_config.get('use_fallback_css', self.use_fallback_css)
            self.extra_css_urls = doc_config.get('extra_css_urls', self.extra_css_urls)
            self.min_content_length = doc_config.get('min_content_length', self.min_content_length)
            
            # Listing filter (nested in document)
            listing_filter = doc_config.get('listing_filter', {})
            if listing_filter:
                include_listing = listing_filter.get('include_listing_pages', False)
                force_include = listing_filter.get('force_include_patterns', [])
                force_exclude = listing_filter.get('force_exclude_patterns', [])
                
                # Merge with existing patterns
                if force_include:
                    self.include_patterns = force_include
                if force_exclude:
                    self.exclude_patterns = force_exclude
        
        # JavaScript rendering settings (may be nested)
        js_config = config.get('javascript_rendering', {})
        if js_config:
            self.js_rendering = js_config.get('enabled', self.js_rendering)
        
        # Crawler settings
        if 'max_retries' in config:
            # Store for later use (not in current dataclass but can be added)
            pass
        if 'timeout_seconds' in config:
            # Store for later use
            pass
        
        self.template_id = template.get('id', 'custom')
    
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        if not self.url or not self.url.startswith('http'):
            return False
        if not self.output_name or not self.output_name.endswith('.docx'):
            return False
        if self.max_pages < 1 or self.max_pages > 1000:
            return False
        if self.crawl_depth < 1 or self.crawl_depth > 5:
            return False
        return True
    
    def get_id(self) -> str:
        """Get unique crawl ID"""
        return self.crawl_id
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'url': self.url,
            'output_name': self.output_name,
            'max_pages': self.max_pages,
            'crawl_depth': self.crawl_depth,
            'strategy': self.strategy,
            'css_selectors': self.css_selectors,
            'parallel': self.parallel,
            'workers': self.workers,
            'include_images': self.include_images,
            'include_code': self.include_code,
            'respect_robots': self.respect_robots,
            'include_patterns': self.include_patterns,
            'exclude_patterns': self.exclude_patterns,
            'strict_base_path': self.strict_base_path,
            'parent_levels': self.parent_levels,
            'url_must_contain': self.url_must_contain,
            'url_must_not_contain': self.url_must_not_contain,
            'js_rendering': self.js_rendering,
            'check_openapi': self.check_openapi,
            'enhanced_html_formatting': self.enhanced_html_formatting,
            'extra_css_urls': self.extra_css_urls,
            'use_fallback_css': self.use_fallback_css,
            'inline_standalone': self.inline_standalone,
            'min_content_length': self.min_content_length,
            'nav_strategy': self.nav_strategy,
            'github_token': self.github_token,
            'github_extensions': self.github_extensions,
            'github_max_files': self.github_max_files,
            'template_id': self.template_id,
            'crawl_id': self.crawl_id
        }
