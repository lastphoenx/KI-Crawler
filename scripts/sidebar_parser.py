#!/usr/bin/env python3

import logging
from typing import List, Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class SidebarParser:
    def __init__(self, base_url: str = "https://docs.pcloud.com"):
        self.base_url = base_url
    
    def extract_navigation_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        nav_div = soup.find('div', class_='docs-nav')
        if not nav_div:
            logger.warning("Could not find docs-nav element")
            return []
        
        # Extract all links from navigation
        for a in nav_div.find_all('a', href=True):
            href = a.get('href', '')
            
            # Skip fragments and empty hrefs
            if not href or href.startswith('#'):
                continue
            
            absolute_url = urljoin(self.base_url, href)
            
            # Skip duplicates
            if absolute_url not in seen:
                seen.add(absolute_url)
                links.append(absolute_url)
        
        return links
    
    def extract_submenu_links(self, html: str, category_url: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        seen = set()
        
        # Look for method lists (each category page lists methods)
        dev_content = soup.find('div', class_='dev-content')
        if not dev_content:
            logger.debug(f"No dev-content in {category_url}")
            return []
        
        for a in dev_content.find_all('a', href=True):
            href = a.get('href', '')
            
            if not href or href.startswith('#'):
                continue
            
            absolute_url = urljoin(category_url, href)
            
            if absolute_url not in seen:
                seen.add(absolute_url)
                links.append(absolute_url)
        
        return links


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    import requests
    
    parser = SidebarParser()
    
    # Test with main page
    print("Fetching main page...")
    response = requests.get("https://docs.pcloud.com/")
    html = response.text
    
    nav_links = parser.extract_navigation_links(html)
    
    print(f"\nFound {len(nav_links)} navigation links:")
    for link in nav_links[:15]:
        print(f"  - {link}")
