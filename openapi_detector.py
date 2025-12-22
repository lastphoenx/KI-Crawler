import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)


class OpenAPIDetector:
    """Detect OpenAPI/Swagger specifications in HTML."""
    
    @staticmethod
    def detect_openapi(html: str, base_url: str) -> Optional[Dict[str, Any]]:
        """
        Detect OpenAPI/Swagger in HTML.
        
        Returns: Dict with keys 'type', 'version', 'url' if found, else None
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        swagger_ui = OpenAPIDetector._detect_swagger_ui(soup, base_url)
        if swagger_ui:
            return swagger_ui
        
        openapi_spec = OpenAPIDetector._detect_openapi_spec_link(soup, base_url)
        if openapi_spec:
            return openapi_spec
        
        json_spec = OpenAPIDetector._detect_json_spec(soup, base_url)
        if json_spec:
            return json_spec
        
        return None
    
    @staticmethod
    def _detect_swagger_ui(soup: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
        """Detect Swagger UI."""
        for script in soup.find_all('script'):
            if script.string:
                if 'swaggerUi' in script.string or 'swagger' in script.string.lower():
                    spec_url = OpenAPIDetector._extract_spec_url(script.string)
                    if spec_url:
                        full_url = urljoin(base_url, spec_url)
                        return {
                            'type': 'swagger_ui',
                            'version': '3.0',
                            'url': full_url
                        }
        
        html_script = soup.find('script', {'src': lambda x: x and 'swagger' in x.lower()})
        if html_script and html_script.get('src'):
            return {
                'type': 'swagger_ui',
                'version': '3.0',
                'url': urljoin(base_url, html_script['src'])
            }
        
        return None
    
    @staticmethod
    def _detect_openapi_spec_link(soup: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
        """Detect OpenAPI spec link in meta tags or links."""
        for link in soup.find_all('link'):
            rel = link.get('rel', [])
            if isinstance(rel, list):
                rel = ' '.join(rel)
            href = link.get('href', '')
            
            if any(x in rel.lower() for x in ['openapi', 'api', 'swagger']):
                full_url = urljoin(base_url, href)
                version = '3.0' if 'openapi' in rel.lower() else '2.0'
                return {
                    'type': 'openapi_link',
                    'version': version,
                    'url': full_url
                }
        
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            
            if 'openapi' in name or 'swagger' in name:
                if content.startswith(('http://', 'https://', '/')):
                    full_url = urljoin(base_url, content)
                    return {
                        'type': 'openapi_meta',
                        'version': '3.0',
                        'url': full_url
                    }
        
        return None
    
    @staticmethod
    def _detect_json_spec(soup: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
        """Detect embedded JSON OpenAPI spec."""
        for script in soup.find_all('script', {'type': 'application/json'}):
            if script.string:
                try:
                    data = json.loads(script.string)
                    
                    if 'swagger' in data:
                        version = data['swagger']
                        return {
                            'type': 'embedded_spec',
                            'version': version,
                            'inline': True
                        }
                    
                    if 'openapi' in data:
                        version = data['openapi']
                        return {
                            'type': 'embedded_spec',
                            'version': version,
                            'inline': True
                        }
                
                except json.JSONDecodeError:
                    continue
        
        return None
    
    @staticmethod
    def _extract_spec_url(script_content: str) -> Optional[str]:
        """Extract spec URL from Swagger UI script."""
        indicators = ['url:', 'urls:', 'spec:', 'specUrl', 'swaggerDoc']
        
        for indicator in indicators:
            if indicator in script_content:
                start = script_content.find(indicator)
                if start != -1:
                    end = script_content.find('"', start)
                    if end != -1:
                        quote_start = script_content.rfind('"', start, end)
                        if quote_start != -1:
                            url = script_content[quote_start + 1:end]
                            if url.startswith(('http://', 'https://', '/', './')):
                                return url
        
        return None
    
    @staticmethod
    def get_common_openapi_paths(base_url: str) -> list:
        """Get common OpenAPI spec paths to check."""
        from urllib.parse import urljoin
        return [
            urljoin(base_url, '/api/openapi.json'),
            urljoin(base_url, '/api/openapi.yaml'),
            urljoin(base_url, '/api/swagger.json'),
            urljoin(base_url, '/openapi.json'),
            urljoin(base_url, '/swagger.json'),
            urljoin(base_url, '/api/v1/openapi.json'),
            urljoin(base_url, '/docs/openapi.json'),
        ]
