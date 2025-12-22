"""
Markdown Documentation Generator
Converts crawled pages to optimized Markdown for RAG/Vector DB
"""

import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import html as html_lib

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generate Markdown documentation from crawled pages for RAG/Vector DB"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('crawler', {}).get('entry_url', '')
    
    def generate(self, pages: Dict[str, Dict], output_dir: Path) -> str:
        """
        Generate single Markdown file with all pages
        
        Args:
            pages: Dict of {url: {'raw_html': html_content}}
            output_dir: Directory to save markdown file
            
        Returns:
            Path to generated markdown file
        """
        try:
            logger.info("Generating Markdown documentation...")
            
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            markdown_file = output_dir / 'documentation.md'
            
            # Parse pages to extract content
            from parser import HTMLParser
            parser = HTMLParser(self.config)
            
            # Collect all markdown content
            md_content = []
            
            # Header with metadata
            md_content.append(f"# Documentation\n")
            md_content.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            md_content.append(f"**Source**: {self.base_url}")
            md_content.append(f"**Pages**: {len(pages)}\n")
            md_content.append("---\n")
            
            # Process each page
            for idx, (url, page_data) in enumerate(pages.items(), 1):
                raw_html = page_data.get('raw_html', '')
                
                if not raw_html:
                    continue
                
                # Parse page to extract structured content
                parsed = parser.parse(raw_html, url)
                
                title = parsed.get('title', 'Untitled')
                elements = parsed.get('elements', [])
                
                # Skip empty pages
                if not elements or not title:
                    continue
                
                # Page header with YAML front matter style
                md_content.append(f"\n## {title}\n")
                md_content.append(f"**Source**: {url}")
                md_content.append(f"**Section**: {idx}\n")
                
                # Convert elements to markdown
                for element in elements:
                    md_element = self._element_to_markdown(element)
                    if md_element:
                        md_content.append(md_element)
                
                # Page separator
                md_content.append("\n---\n")
            
            # Write markdown file
            markdown_text = '\n'.join(md_content)
            
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            file_size_mb = markdown_file.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Generated Markdown: {markdown_file}")
            logger.info(f"   Size: {file_size_mb:.2f} MB")
            logger.info(f"   Pages: {len(pages)}")
            
            return str(markdown_file)
            
        except Exception as e:
            logger.error(f"Failed to generate Markdown: {e}", exc_info=True)
            return None
    
    def _element_to_markdown(self, element: Dict[str, Any]) -> str:
        """Convert a parsed element to Markdown"""
        elem_type = element.get('type', 'unknown')
        text = element.get('text', '')
        
        # Sanitize text
        if text:
            text = html_lib.unescape(text).strip()
        
        # Headings - use proper hierarchy for RAG chunking
        if elem_type == 'heading_1':
            return f"# {text}\n"
        elif elem_type == 'heading_2':
            return f"## {text}\n"
        elif elem_type == 'heading_3':
            return f"### {text}\n"
        elif elem_type == 'heading_4':
            return f"#### {text}\n"
        elif elem_type == 'heading_5':
            return f"##### {text}\n"
        elif elem_type == 'heading_6':
            return f"###### {text}\n"
        
        # Regular paragraphs and text
        elif elem_type in ('paragraph', 'text'):
            if text:
                return f"{text}\n"
        
        # Code blocks and inline code
        elif elem_type == 'code_block':
            if text:
                # Try to detect language for syntax highlighting
                return f"```\n{text}\n```\n"
        elif elem_type == 'code_inline':
            if text:
                return f"`{text}`\n"
        
        # Lists
        elif elem_type == 'list_unordered':
            items = element.get('items', [])
            if items:
                md_list = '\n'.join([f"- {html_lib.unescape(item.strip())}" for item in items if item.strip()])
                return f"{md_list}\n"
        
        elif elem_type == 'list_ordered':
            items = element.get('items', [])
            if items:
                md_list = '\n'.join([f"{i}. {html_lib.unescape(item.strip())}" for i, item in enumerate(items, 1) if item.strip()])
                return f"{md_list}\n"
        
        # Definition lists
        elif elem_type == 'definition_list' or elem_type == 'definition':
            items = element.get('items', [])
            if items:
                md_list = []
                for item in items:
                    term = item.get('term', '').strip()
                    definition = item.get('definition', '').strip()
                    if term:
                        md_list.append(f"**{html_lib.unescape(term)}**")
                        if definition:
                            md_list.append(f": {html_lib.unescape(definition)}")
                return '\n'.join(md_list) + '\n'
            # Single definition item
            elif elem_type == 'definition':
                term = element.get('term', '').strip()
                definition = element.get('definition', '').strip()
                if term:
                    result = f"**{html_lib.unescape(term)}**"
                    if definition:
                        result += f": {html_lib.unescape(definition)}"
                    return result + '\n'
        
        # Tables
        elif elem_type == 'table':
            rows = element.get('rows', [])
            if rows:
                return self._table_to_markdown(rows)
        
        # Blockquotes and info boxes
        elif elem_type == 'blockquote':
            if text:
                return f"> {text}\n"
        
        elif elem_type == 'info_box':
            if text:
                return f"> **ℹ️ {text}**\n"
        
        return None
    
    def _table_to_markdown(self, rows: List[List[str]]) -> str:
        """Convert table rows to Markdown table"""
        if not rows:
            return ""
        
        # Header row
        header = rows[0]
        md_lines = [
            "| " + " | ".join([str(h).strip() for h in header]) + " |",
            "|" + "|".join([" --- " for _ in header]) + "|"
        ]
        
        # Body rows
        for row in rows[1:]:
            md_lines.append("| " + " | ".join([str(cell).strip() for cell in row]) + " |")
        
        return '\n'.join(md_lines) + '\n'
