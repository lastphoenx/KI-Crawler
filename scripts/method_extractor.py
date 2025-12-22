import logging
from typing import List, Set, Dict
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MethodExtractor:
    def __init__(self):
        pass
    
    def extract_method_urls(self, pages: Dict[str, Dict]) -> List[str]:
        """
        Extract all method URLs from category pages.
        
        Args:
            pages: Dict from crawler with URL -> {'raw_html': ...} structure
            
        Returns:
            List of method URLs to crawl
        """
        method_urls: Set[str] = set()
        
        for url, page_data in pages.items():
            html = page_data.get('raw_html', '')
            if not html:
                continue
            
            try:
                soup = BeautifulSoup(html, 'html.parser')
                dev_content = soup.find('div', class_='dev-content')
                
                if not dev_content:
                    continue
                
                logger.info(f"Extracting method links from: {url}")
                
                for link in dev_content.find_all('a', href=True):
                    href = link['href']
                    
                    if not href or href.startswith('#'):
                        continue
                    
                    absolute_url = urljoin(url, href)
                    
                    if absolute_url.endswith('.html'):
                        method_urls.add(absolute_url)
                        logger.debug(f"  Found: {absolute_url}")
            
            except Exception as e:
                logger.error(f"Error extracting links from {url}: {e}")
                continue
        
        result = sorted(list(method_urls))
        logger.info(f"Total unique method URLs found: {len(result)}")
        return result
