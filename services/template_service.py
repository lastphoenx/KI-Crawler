"""
Template service for predefined crawler configurations
"""

from typing import Dict, List


class TemplateService:
    """Manages predefined templates for different documentation types"""
    
    TEMPLATES = {
        'custom': {
            'id': 'custom',
            'name': 'Custom',
            'icon': '⚙️',
            'description': 'Configure everything manually',
            'config': {
                'strategy': 'css',
                'css_selectors': [],
                'max_pages': 100,
                'crawl_depth': 2,
                'parallel': True,
                'workers': 5
            }
        },
        'pcloud': {
            'id': 'pcloud',
            'name': 'pCloud API',
            'icon': '☁️',
            'description': 'Optimized for pCloud API documentation',
            'config': {
                'url': 'https://docs.pcloud.com/methods/',
                'strategy': 'pcloud',
                'nav_strategy': 'pcloud',  # Use PCloudNavigationStrategy
                'css_selectors': ['nav.side-nav a', 'div.dev-content a'],
                'max_pages': 100,
                'crawl_depth': 2,
                'parallel': True,
                'workers': 5,
                'include_patterns': ['.*/methods/.*'],
                'api_format': 'custom'
            }
        },
        'github': {
            'id': 'github',
            'name': 'GitHub Repository',
            'icon': '🐙',
            'description': 'Crawl GitHub repository files via API',
            'config': {
                'url': 'https://github.com/owner/repo',
                'strategy': 'github',
                'nav_strategy': 'github',  # Use GitHubNavigationStrategy
                'max_pages': 200,
                'crawl_depth': 1,
                'parallel': True,
                'workers': 5,
                'github_max_files': 300,
                'github_extensions': ['.md', '.txt', '.py', '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.sh']
            }
        },
        'readthedocs': {
            'id': 'readthedocs',
            'name': 'ReadTheDocs',
            'icon': '📖',
            'description': 'Standard ReadTheDocs structure',
            'config': {
                'strategy': 'readthedocs',
                'css_selectors': ['nav.wy-nav-side a', 'div.toctree-wrapper a'],
                'max_pages': 150,
                'crawl_depth': 3,
                'parallel': True,
                'workers': 5
            }
        },
        'stripe': {
            'id': 'stripe',
            'name': 'Stripe API',
            'icon': '💳',
            'description': 'Stripe API documentation',
            'config': {
                'url': 'https://stripe.com/docs/api',
                'strategy': 'sitemap',
                'max_pages': 200,
                'crawl_depth': 2,
                'parallel': True,
                'workers': 5,
                'check_openapi': True
            }
        }
    }
    
    def get_all_templates(self) -> List[Dict]:
        """Get all available templates (hardcoded + saved custom)"""
        import json
        from pathlib import Path
        
        # Start with hardcoded templates
        all_templates = list(self.TEMPLATES.values())
        
        # Load saved custom templates from templates/ directory
        templates_dir = Path(__file__).parent.parent / 'templates'
        if templates_dir.exists():
            for template_file in templates_dir.glob('*.json'):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        custom_template = json.load(f)
                        # Add to list if not already in hardcoded templates
                        if custom_template.get('id') not in self.TEMPLATES:
                            all_templates.append(custom_template)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to load template {template_file}: {e}")
        
        return all_templates
    
    def get_template(self, template_id: str) -> Dict:
        """Get a specific template by ID"""
        return self.TEMPLATES.get(template_id, self.TEMPLATES['custom'])
    
    def get_template_names(self) -> List[str]:
        """Get list of template names"""
        return [t['name'] for t in self.TEMPLATES.values()]
    
    def save_template(self, template: Dict) -> bool:
        """Save a custom template"""
        import json
        from pathlib import Path
        
        # Save to templates directory
        templates_dir = Path(__file__).parent.parent / 'templates'
        templates_dir.mkdir(exist_ok=True)
        
        template_id = template.get('id', 'custom')
        template_file = templates_dir / f"{template_id}.json"
        
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2)
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to save template: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a custom template"""
        from pathlib import Path
        
        # Cannot delete hardcoded templates
        if template_id in self.TEMPLATES:
            return False
        
        templates_dir = Path(__file__).parent.parent / 'templates'
        template_file = templates_dir / f"{template_id}.json"
        
        try:
            if template_file.exists():
                template_file.unlink()
                return True
            return False
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to delete template: {e}")
            return False
