import logging
from typing import Set, Optional
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import requests

logger = logging.getLogger(__name__)


class SitemapParser:
    """Parse sitemap.xml and extract URLs."""
    
    def __init__(self, user_agent: str = "Mozilla/5.0"):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    def fetch_sitemaps(self, base_url: str) -> Set[str]:
        """
        Fetch and parse sitemap(s) from base_url.
        Tries both XML sitemap and HTML sitemap.
        Handles sitemap index (references multiple sitemaps).
        
        Returns: Set of URLs found in sitemaps
        """
        urls = set()
        parsed = urlparse(base_url)
        domain = parsed.netloc
        scheme = parsed.scheme or "https"
        
        # Try XML sitemap first (standard) - use scheme from entry URL
        sitemap_url = f"{scheme}://{domain}/sitemap.xml"
        
        try:
            logger.info(f"Fetching sitemap from: {sitemap_url}")
            response = self.session.get(sitemap_url, timeout=10)
            response.raise_for_status()
            
            # Check if response is actually XML (not 404 HTML page)
            if 'xml' in response.headers.get('Content-Type', '').lower() or response.text.strip().startswith('<?xml'):
                urls = self._parse_sitemap(response.text, base_url)
                logger.info(f"Extracted {len(urls)} URLs from XML sitemap")
                return urls
            
        except requests.RequestException as e:
            logger.debug(f"XML sitemap not found: {e}")
        
        # Try HTML sitemap as fallback (common patterns)
        html_sitemap_patterns = [
            f"{parsed.scheme}://{domain}/sitemap.html",
            f"{parsed.scheme}://{domain}/Sitemap.html",
            f"{parsed.scheme}://{domain}/sitemap/",
            f"{parsed.scheme}://{domain}/de/Sitemap.html",  # German sites
            f"{parsed.scheme}://{domain}/en/sitemap.html",  # English sites
        ]
        
        for html_sitemap_url in html_sitemap_patterns:
            try:
                logger.info(f"Trying HTML sitemap: {html_sitemap_url}")
                response = self.session.get(html_sitemap_url, timeout=10)
                if response.status_code == 200 and 'html' in response.headers.get('Content-Type', '').lower():
                    urls = self._parse_html_sitemap(response.text, base_url)
                    if urls:
                        logger.info(f"✅ Extracted {len(urls)} URLs from HTML sitemap")
                        return urls
            except requests.RequestException:
                continue
        
        logger.warning("No sitemap found (tried XML and HTML)")
        return urls
    
    def _parse_sitemap(self, xml_content: str, base_url: str) -> Set[str]:
        """Parse sitemap XML and extract URLs."""
        urls = set()
        
        try:
            root = ET.fromstring(xml_content)
            ns = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            # Check if this is a sitemap index
            sitemaps = root.findall('sitemap:sitemap', ns)
            if sitemaps:
                for sitemap in sitemaps:
                    loc = sitemap.find('sitemap:loc', ns)
                    if loc is not None and loc.text:
                        urls.update(self._fetch_child_sitemap(loc.text, base_url))
            else:
                # Regular sitemap with URL entries
                url_entries = root.findall('sitemap:url', ns)
                for url_entry in url_entries:
                    loc = url_entry.find('sitemap:loc', ns)
                    if loc is not None and loc.text:
                        urls.add(loc.text)
        
        except ET.ParseError as e:
            logger.warning(f"Could not parse sitemap XML: {e}")
        
        return urls
    
    def _fetch_child_sitemap(self, sitemap_url: str, base_url: str) -> Set[str]:
        """Fetch and parse a child sitemap from sitemap index."""
        urls = set()
        
        try:
            response = self.session.get(sitemap_url, timeout=10)
            response.raise_for_status()
            urls = self._parse_sitemap(response.text, base_url)
        except requests.RequestException as e:
            logger.warning(f"Could not fetch child sitemap {sitemap_url}: {e}")
        
        return urls
    
    def _parse_html_sitemap(self, html_content: str, base_url: str) -> Set[str]:
        """Parse HTML sitemap and extract all links."""
        from bs4 import BeautifulSoup
        urls = set()
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all links in the sitemap
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Only include links from same domain
                if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                    urls.add(absolute_url)
            
            logger.debug(f"Found {len(urls)} links in HTML sitemap")
        
        except Exception as e:
            logger.warning(f"Could not parse HTML sitemap: {e}")
        
        return urls
