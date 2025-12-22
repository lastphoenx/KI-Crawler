import logging
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup, NavigableString, Tag
import json

logger = logging.getLogger(__name__)


class HTMLParser:
    def __init__(self, config: Dict):
        self.config = config['parser']
    
    def _find_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        selectors = self.config.get('content_selectors', [])
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element
        return soup.find('body')
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        selectors = self.config.get('title_selectors', [])
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        return "Untitled"
    
    def _clean_text(self, text: str) -> str:
        lines = text.split('\n')
        cleaned = [line.strip() for line in lines if line.strip()]
        return '\n'.join(cleaned)
    
    def _parse_definition_list(self, dl: Tag) -> List[Dict[str, Any]]:
        result = []
        dts = dl.find_all('dt', recursive=False)
        
        for dt in dts:
            term = dt.get_text(strip=True)
            dd = dt.find_next_sibling('dd')
            if dd:
                definition = dd.get_text(strip=True)
                result.append({
                    'type': 'definition',
                    'term': term,
                    'definition': definition
                })
        
        return result
    
    def _parse_element(self, element: Tag) -> Dict[str, Any]:
        if isinstance(element, NavigableString):
            return None
        
        tag_name = element.name.lower() if element.name else None
        
        if tag_name in ['script', 'style', 'nav', 'footer', 'header']:
            return None
        
        if tag_name == 'h1':
            return {
                'type': 'heading_1',
                'text': element.get_text(strip=True)
            }
        elif tag_name == 'h2':
            return {
                'type': 'heading_2',
                'text': element.get_text(strip=True)
            }
        elif tag_name == 'h3':
            return {
                'type': 'heading_3',
                'text': element.get_text(strip=True)
            }
        elif tag_name == 'h4':
            return {
                'type': 'heading_4',
                'text': element.get_text(strip=True)
            }
        elif tag_name == 'p':
            text = element.get_text(strip=True)
            if text:
                return {
                    'type': 'paragraph',
                    'text': text
                }
        elif tag_name == 'code':
            return {
                'type': 'code_inline',
                'text': element.get_text()
            }
        elif tag_name == 'pre':
            return {
                'type': 'code_block',
                'text': element.get_text()
            }
        elif tag_name == 'ul':
            items = [li.get_text(strip=True) for li in element.find_all('li', recursive=False)]
            if items:
                return {
                    'type': 'list_unordered',
                    'items': items
                }
        elif tag_name == 'ol':
            items = [li.get_text(strip=True) for li in element.find_all('li', recursive=False)]
            if items:
                return {
                    'type': 'list_ordered',
                    'items': items
                }
        elif tag_name == 'table':
            rows = self._parse_table(element)
            if rows:
                return {
                    'type': 'table',
                    'rows': rows
                }
        elif tag_name == 'dl':
            items = self._parse_definition_list(element)
            if items:
                return {
                    'type': 'definition_list',
                    'items': items
                }
        elif tag_name == 'blockquote':
            text = element.get_text(strip=True)
            if text:
                return {
                    'type': 'blockquote',
                    'text': text
                }
        elif tag_name == 'div':
            classes = ' '.join(element.get('class', []))
            
            if any(keyword in classes.lower() for keyword in ['note', 'warning', 'info', 'alert', 'box']):
                text = element.get_text(strip=True)
                if text:
                    return {
                        'type': 'info_box',
                        'text': text,
                        'style': classes
                    }
            
            # Don't skip divs - they might contain important content
            return None
        
        return None
    
    def _parse_table(self, table: Tag) -> List[List[str]]:
        rows = []
        for tr in table.find_all('tr'):
            cols = []
            for td in tr.find_all(['td', 'th']):
                cols.append(td.get_text(strip=True))
            if cols:
                rows.append(cols)
        return rows
    
    def _extract_all_elements(self, element: Tag) -> List[Dict[str, Any]]:
        elements = []
        
        for child in element.children:
            if isinstance(child, NavigableString):
                text = child.strip()
                if text and len(text) > 2:
                    elements.append({
                        'type': 'text',
                        'text': text
                    })
            else:
                parsed = self._parse_element(child)
                if parsed:
                    elements.append(parsed)
                else:
                    # Only recurse if element was NOT fully parsed (to avoid duplication)
                    tag_name = child.name.lower() if child.name else None
                    if tag_name and tag_name not in ['table', 'ul', 'ol', 'dl', 'pre', 'code', 'li', 'tr', 'td', 'th', 'dt', 'dd', 'script', 'style', 'nav', 'footer', 'header']:
                        nested = self._extract_all_elements(child)
                        elements.extend(nested)
        
        return elements
    
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        try:
            # Detect if this is plain text (e.g., GitHub raw URLs)
            is_raw_content = 'raw.githubusercontent.com' in url or not html.strip().startswith('<')
            
            if is_raw_content:
                # Treat as plain text, not HTML
                # Extract filename from URL for title
                filename = url.split('/')[-1] if '/' in url else 'Untitled'
                
                # Split into paragraphs (blank line separated)
                lines = html.strip().split('\n')
                paragraphs = []
                current_para = []
                
                for line in lines:
                    if line.strip():
                        current_para.append(line)
                    elif current_para:
                        paragraphs.append('\n'.join(current_para))
                        current_para = []
                
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                
                # Convert to elements
                elements = []
                for para in paragraphs[:100]:  # Limit to 100 paragraphs
                    if para.strip():
                        # Check if it looks like code (indented or has symbols)
                        is_code = para.startswith((' ', '\t', '#', '/', 'def ', 'class ', 'import ', 'from '))
                        elements.append({
                            'type': 'code_block' if is_code else 'paragraph',
                            'text': para
                        })
                
                return {
                    'url': url,
                    'title': filename,
                    'elements': elements,
                    'error': None
                }
            
            # Regular HTML parsing
            soup = BeautifulSoup(html, 'html.parser')
            
            title = self._extract_title(soup)
            content_elem = self._find_content(soup)
            
            elements = []
            if content_elem:
                elements = self._extract_all_elements(content_elem)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_elements = []
            for elem in elements:
                elem_key = (elem.get('type'), elem.get('text', '')[:100])
                if elem_key not in seen:
                    seen.add(elem_key)
                    unique_elements.append(elem)
            
            return {
                'url': url,
                'title': title,
                'elements': unique_elements[:100],  # Limit to 100 elements per page
                'error': None
            }
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return {
                'url': url,
                'title': 'Error',
                'elements': [],
                'error': str(e)
            }


class PageData:
    def __init__(self, url: str, title: str, elements: List[Dict], error: Optional[str] = None):
        self.url = url
        self.title = title
        self.elements = elements
        self.error = error
    
    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'title': self.title,
            'elements': self.elements,
            'error': self.error
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
