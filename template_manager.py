"""Template management for DOCX output."""

import logging
from typing import Dict, List, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DocumentTemplate(ABC):
    """Abstract base class for document templates."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Template name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Template description."""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get template configuration."""
        pass


class StandardTemplate(DocumentTemplate):
    """Professional standard template (balanced)."""
    
    @property
    def name(self) -> str:
        return "Standard"
    
    @property
    def description(self) -> str:
        return "Professional documentation for all audiences"
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'include_code': True,
            'include_images': True,
            'include_parameters': True,
            'include_examples': True,
            'code_detail': 'medium',
            'syntax_highlighting': True,
            'include_toc': True,
            'title_page': True,
            'image_max_width': 5.0,
            'code_max_lines': 50,
            'include_raw_json': False,
        }


class DeveloperTemplate(DocumentTemplate):
    """Developer template (verbose code, full technical details)."""
    
    @property
    def name(self) -> str:
        return "Developer"
    
    @property
    def description(self) -> str:
        return "Technical documentation with full code and API details"
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'include_code': True,
            'include_images': False,
            'include_parameters': True,
            'include_examples': True,
            'code_detail': 'full',
            'syntax_highlighting': True,
            'include_toc': True,
            'title_page': True,
            'image_max_width': 4.0,
            'code_max_lines': 200,
            'include_raw_json': True,
            'include_curl_examples': True,
        }


class CompactTemplate(DocumentTemplate):
    """Compact template (minimal, quick reference)."""
    
    @property
    def name(self) -> str:
        return "Compact"
    
    @property
    def description(self) -> str:
        return "Quick reference - essential information only"
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'include_code': True,
            'include_images': False,
            'include_parameters': True,
            'include_examples': False,
            'code_detail': 'minimal',
            'syntax_highlighting': False,
            'include_toc': False,
            'title_page': False,
            'code_max_lines': 20,
            'include_raw_json': False,
        }


class TemplateManager:
    """Manage available document templates."""
    
    TEMPLATES = {
        'standard': StandardTemplate,
        'developer': DeveloperTemplate,
        'compact': CompactTemplate,
    }
    
    @classmethod
    def get_template(cls, name: str) -> DocumentTemplate:
        """Get template by name."""
        if name not in cls.TEMPLATES:
            logger.warning(f"Unknown template: {name}. Using 'standard'.")
            name = 'standard'
        
        return cls.TEMPLATES[name]()
    
    @classmethod
    def list_templates(cls) -> Dict[str, str]:
        """List all available templates with descriptions."""
        return {
            name: cls.TEMPLATES[name]().description
            for name in cls.TEMPLATES.keys()
        }
    
    @classmethod
    def get_default_template(cls) -> DocumentTemplate:
        """Get default template."""
        return cls.get_template('standard')
