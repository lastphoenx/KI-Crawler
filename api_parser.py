import logging
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup, Tag, NavigableString
import re

logger = logging.getLogger(__name__)


class APIMethodParser:
    def __init__(self):
        pass
    
    def _extract_dl_data(self, dl: Tag) -> Dict[str, str]:
        """Extract key-value pairs from definition list"""
        data = {}
        if not dl or dl.name != 'dl':
            return data
        
        dts = dl.find_all('dt', recursive=False)
        for dt in dts:
            key = dt.get_text(strip=True).lower()
            dd = dt.find_next_sibling('dd')
            if dd:
                value = dd.get_text(strip=True)
                data[key] = value
        
        return data
    
    def _extract_table_as_list(self, table: Tag) -> List[Dict[str, str]]:
        """Extract table rows as list of dicts"""
        if not table or table.name != 'table':
            return []
        
        rows = table.find_all('tr')
        if not rows:
            return []
        
        headers = []
        header_row = rows[0]
        for th in header_row.find_all(['th', 'td']):
            headers.append(th.get_text(strip=True).lower())
        
        result = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if cells:
                row_dict = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row_dict[headers[i]] = cell.get_text(strip=True)
                result.append(row_dict)
        
        return result
    
    def _split_parameters(self, param_section: str) -> Tuple[List[Dict], List[Dict]]:
        """Try to split parameters into Required/Optional"""
        required = []
        optional = []
        
        lines = param_section.split('\n')
        current_section = 'required'
        
        for line in lines:
            line = line.strip()
            if 'required' in line.lower():
                current_section = 'required'
            elif 'optional' in line.lower():
                current_section = 'optional'
            elif line and not line.startswith('Name'):
                cells = [c.strip() for c in line.split('\t') if c.strip()]
                if len(cells) >= 2:
                    entry = {
                        'name': cells[0],
                        'type': cells[1] if len(cells) > 1 else '',
                        'description': cells[2] if len(cells) > 2 else ''
                    }
                    if current_section == 'required':
                        required.append(entry)
                    else:
                        optional.append(entry)
        
        return required, optional
    
    def _detect_method_page(self, soup: BeautifulSoup) -> bool:
        """Detect if page is an API method page"""
        content = soup.select_one('div.dev-content')
        if not content:
            return False
        
        has_h2 = content.find('h2')
        has_dl = content.find('dl')
        has_auth_field = content.get_text().lower().find('auth') > -1
        
        return bool(has_h2 and has_dl and has_auth_field)
    
    def parse_method_page(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse API method page and extract structured data"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            if not self._detect_method_page(soup):
                return None
            
            content = soup.select_one('div.dev-content')
            if not content:
                return None
            
            method_data = {
                'url': url,
                'type': 'api_method',
                'name': None,
                'auth': None,
                'description': None,
                'notes': [],
                'parameters': {'required': [], 'optional': []},
                'output': [],
                'example': None,
                'errors': [],
                'api_url': None
            }
            
            h2 = content.find('h2')
            if h2:
                method_data['name'] = h2.get_text(strip=True)
            
            dl = content.find('dl')
            if dl:
                dl_data = self._extract_dl_data(dl)
                method_data['auth'] = dl_data.get('auth')
                method_data['description'] = dl_data.get('description')
                
                output_text = dl_data.get('output', '')
                if output_text:
                    example_text = dl_data.get('example', '')
                    method_data['example'] = example_text
            
            output_table = content.find('table', {'class': 'dev-table-full'})
            if output_table:
                method_data['output'] = self._extract_table_as_list(output_table)
            
            all_tables = content.find_all('table', {'class': 'dev-table-full'})
            if len(all_tables) > 1:
                method_data['errors'] = self._extract_table_as_list(all_tables[-1])
            
            pre = content.find('pre')
            if pre:
                method_data['example'] = pre.get_text()
            
            method_data['api_url'] = self._extract_api_url(method_data['name'], url)
            
            return method_data if method_data['name'] else None
            
        except Exception as e:
            logger.error(f"Error parsing method page {url}: {e}")
            return None
    
    def _extract_api_url(self, method_name: Optional[str], doc_url: str) -> str:
        """Extract API URL from method name and doc URL"""
        if not method_name:
            return ""
        
        base_url = "https://api.pcloud.com"
        
        try:
            if '/methods/general/' in doc_url:
                return f"{base_url}/{method_name}"
            elif '/methods/' in doc_url:
                category = doc_url.split('/methods/')[1].split('/')[0]
                return f"{base_url}/{method_name}"
        except:
            pass
        
        return f"{base_url}/{method_name}"
    
    def is_method_page(self, html: str, url: str) -> bool:
        """Check if HTML content is an API method page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return self._detect_method_page(soup)
        except:
            return False
