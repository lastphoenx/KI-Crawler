"""
New Crawl Page - Configuration form for starting a new crawl
"""

from nicegui import ui
from models.crawl_config import CrawlConfig
from services.template_service import TemplateService
from services.crawler_service import CrawlerService
import re


class NewCrawlPage:
    """New crawl configuration page"""
    
    def __init__(self, prefill_url: str = None, template: str = None):
        self.template_service = TemplateService()
        self.crawler_service = CrawlerService()
        self.config = CrawlConfig()
        self.selected_template = template if template else 'custom'
        self.prefill_url = prefill_url
        
        # Load template if specified
        if template:
            template_obj = self.template_service.get_template(template)
            if template_obj and template_obj['config']:
                # Apply template config to crawl config
                for key, value in template_obj['config'].items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
                import logging
                logging.getLogger(__name__).info(f"Loaded template: {template}")
        
        # UI references for updates
        self.url_input = None
        self.output_input = None
        self.max_pages_slider = None
        self.max_pages_label = None
        self.depth_slider = None
        self.depth_label = None
        self.strategy_select = None
        self.css_textarea = None
        self.include_patterns = None
        self.exclude_patterns = None
        self.template_cards = {}  # Store card references for visual updates
    
    def render(self):
        """Render the new crawl page"""
        with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-8'):
            # Header
            with ui.row().classes('w-full items-center mb-4'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/'))\
                    .props('flat round')
                ui.label('New Crawl').classes('text-3xl font-bold ml-4')
            
            # Step 1: Template Selection
            self._render_template_selector()
            
            ui.separator().classes('my-6')
            
            # Step 2: Configuration Form
            self._render_config_form()
            
            ui.separator().classes('my-6')
            
            # Action Buttons
            self._render_actions()
    
    def _render_template_selector(self):
        """Render template selection cards"""
        ui.label('Step 1: Choose Template').classes('text-2xl font-semibold mb-4')
        ui.label('Select a pre-configured template or start from scratch').classes('text-gray-600 mb-4')
        
        templates = self.template_service.get_all_templates()
        
        with ui.row().classes('gap-4 mb-6 flex-wrap'):
            for template in templates:
                self._template_card(template)
    
    def _template_card(self, template):
        """Render a single template card"""
        is_selected = self.selected_template == template['id']
        
        card_classes = (
            'cursor-pointer transition-all hover-lift '
            f"{'border-2 border-indigo-600 bg-indigo-50' if is_selected else 'border border-gray-300'}"
        )
        
        card = ui.card().classes(card_classes)\
                .on('click', lambda t=template: self._select_template(t))\
                .style('min-width: 150px; max-width: 200px')
        
        # Store reference for later updates
        self.template_cards[template['id']] = card
        
        with card:
            with ui.column().classes('items-center p-4 gap-2'):
                ui.label(template['icon']).classes('text-5xl')
                ui.label(template['name']).classes('font-bold text-lg')
                ui.label(template['description']).classes('text-sm text-gray-600 text-center')
                
                # Selection indicator
                check_icon = ui.icon('check_circle').classes('text-indigo-600 text-2xl mt-2')
                check_icon.visible = is_selected
                
                # Store check icon reference
                if not hasattr(self, 'template_check_icons'):
                    self.template_check_icons = {}
                self.template_check_icons[template['id']] = check_icon
    
    def _select_template(self, template):
        """Handle template selection"""
        old_template = self.selected_template
        self.selected_template = template['id']
        
        # Update visual state of all cards
        for tid, card in self.template_cards.items():
            if tid == template['id']:
                # Selected card
                card.classes(replace='cursor-pointer transition-all hover-lift border-2 border-indigo-600 bg-indigo-50')
                if hasattr(self, 'template_check_icons') and tid in self.template_check_icons:
                    self.template_check_icons[tid].visible = True
            else:
                # Unselected cards
                card.classes(replace='cursor-pointer transition-all hover-lift border border-gray-300')
                if hasattr(self, 'template_check_icons') and tid in self.template_check_icons:
                    self.template_check_icons[tid].visible = False
        
        # Load template config
        if template['id'] != 'custom':
            self.config.load_from_template(template)
            self._update_form_values()
        
        ui.notify(f"Template '{template['name']}' selected", type='positive')
    
    def _render_config_form(self):
        """Render the configuration form"""
        ui.label('Step 2: Configure Crawl').classes('text-2xl font-semibold mb-4')
        
        with ui.card().classes('w-full p-6'):
            # Basic Settings
            ui.label('Basic Settings').classes('text-lg font-semibold mb-4')
            
            # URL Input
            self.url_input = ui.input(
                'Start URL*',
                placeholder='https://docs.example.com',
                value=self.prefill_url or self.config.url
            ).classes('w-full mb-4').props('outlined')
            self.url_input.on('change', lambda: setattr(self.config, 'url', self.url_input.value))
            
            # Update config with prefilled URL
            if self.prefill_url:
                self.config.url = self.prefill_url
            
            # Output Name
            self.output_input = ui.input(
                'Output Filename*',
                placeholder='documentation.docx',
                value=self.config.output_name
            ).classes('w-full mb-4').props('outlined')
            self.output_input.on('change', lambda: setattr(self.config, 'output_name', self.output_input.value))
            
            # Sliders
            with ui.row().classes('w-full gap-8 mb-4'):
                # Max Pages
                with ui.column().classes('flex-1'):
                    ui.label('Max Pages').classes('font-medium mb-2')
                    with ui.row().classes('w-full items-center gap-4'):
                        self.max_pages_slider = ui.slider(
                            min=1, max=1000, value=self.config.max_pages, step=10
                        ).classes('flex-1')
                        self.max_pages_label = ui.label(str(self.config.max_pages))\
                            .classes('font-bold text-lg w-16')
                    
                    self.max_pages_slider.on('change', lambda: self._update_max_pages(self.max_pages_slider.value))
                
                # Crawl Depth
                with ui.column().classes('flex-1'):
                    ui.label('Crawl Depth').classes('font-medium mb-2')
                    with ui.row().classes('w-full items-center gap-4'):
                        self.depth_slider = ui.slider(
                            min=1, max=5, value=self.config.crawl_depth
                        ).classes('flex-1')
                        self.depth_label = ui.label(str(self.config.crawl_depth))\
                            .classes('font-bold text-lg w-16')
                    
                    self.depth_slider.on('change', lambda: self._update_depth(self.depth_slider.value))
            
            # Advanced Settings (Expandable)
            with ui.expansion('⚙️ Advanced Settings', icon='settings').classes('w-full'):
                self._render_advanced_settings()
    
    def _render_advanced_settings(self):
        """Render advanced configuration options"""
        with ui.column().classes('w-full p-4 gap-4'):
            # Navigation Strategy
            ui.label('Navigation Strategy').classes('font-semibold text-lg mb-2')
            ui.label('Determines how the crawler discovers pages to crawl').classes('text-sm text-gray-600 mb-2')
            self.strategy_select = ui.select(
                options={
                    'pcloud': 'pCloud API (docs-nav based)',
                    'generic': 'Generic (nav/main links)',
                    'github': 'GitHub Repository (API)'
                },
                value='pcloud',
                label='Navigation Strategy'
            ).classes('w-full')
            
            # GitHub-specific options (conditional)
            with ui.column().classes('w-full gap-3 mt-4') as self.github_options:
                ui.label('GitHub Options').classes('font-semibold text-gray-700')
                ui.label('File extensions to include:').classes('text-sm text-gray-600')
                self.github_extensions_input = ui.input(
                    placeholder='.md, .txt, .py, .json, .yml',
                    value=', '.join(self.config.github_extensions)
                ).classes('w-full')
                
                self.github_max_files = ui.number(
                    'Max Files',
                    value=self.config.github_max_files,
                    min=10,
                    max=1000
                ).classes('w-full')
            
            # Show/hide GitHub options based on strategy
            self.github_options.visible = (self.config.nav_strategy == 'github')
            
            def on_strategy_change(value):
                setattr(self.config, 'nav_strategy', value)
                self.github_options.visible = (value == 'github')
                ui.notify(f'Navigation strategy: {value}', type='info')
            
            self.strategy_select.on('change', lambda e: on_strategy_change(e.value))
            
            # Checkboxes
            ui.label('Content Options').classes('font-semibold text-lg mt-4 mb-2')
            with ui.row().classes('gap-8'):
                with ui.column().classes('gap-2'):
                    ui.checkbox('Include Images', value=True)\
                        .on('change', lambda e: setattr(self.config, 'include_images', e.value))
                    ui.checkbox('Include Code Blocks', value=True)\
                        .on('change', lambda e: setattr(self.config, 'include_code', e.value))
                
                with ui.column().classes('gap-2'):
                    parallel_cb = ui.checkbox('Parallel Crawling (5x faster)', value=True)\
                        .on('change', lambda e: setattr(self.config, 'parallel', e.value))
                    ui.checkbox('Respect robots.txt', value=True)\
                        .on('change', lambda e: setattr(self.config, 'respect_robots', e.value))
            
            # HTML Formatting Options
            ui.label('HTML Output Formatting').classes('font-semibold text-lg mt-4 mb-2')
            ui.label('Enhanced HTML formatting improves readability with structured tables and definition lists').classes('text-sm text-gray-600 mb-2')
            self.enhanced_html_cb = ui.checkbox('Enhanced HTML Formatting (experimental)', value=self.config.enhanced_html_formatting)\
                .on('change', lambda e: setattr(self.config, 'enhanced_html_formatting', e.value))
            self.fallback_css_cb = ui.checkbox('Use Fallback CSS (hardcoded pCloud URLs)', value=self.config.use_fallback_css)\
                .on('change', lambda e: setattr(self.config, 'use_fallback_css', e.value))
            ui.label('Fallback CSS helps if extraction fails. Disable to test extraction only.').classes('text-xs text-gray-500 mb-2')
            
            self.inline_standalone_cb = ui.checkbox('Generate Standalone HTML (single-file with inline assets)', value=self.config.inline_standalone)\
                .on('change', lambda e: setattr(self.config, 'inline_standalone', e.value))
            ui.label('Creates index-standalone.html with all CSS/images/fonts inlined as Base64. Larger file but portable.').classes('text-xs text-gray-500 mb-2')
            
            # Minimum content length filter
            with ui.row().classes('gap-2 items-center mt-2'):
                ui.label('Min Content Length:').classes('text-sm')
                self.min_content_length_input = ui.number(label='', value=self.config.min_content_length, min=0, max=1000, step=10)\
                    .classes('w-32')\
                    .on('change', lambda e: setattr(self.config, 'min_content_length', int(e.value) if e.value else 0))
                ui.label('chars (0 = keep all pages)').classes('text-xs text-gray-500')
            ui.label('Pages with less text will be filtered as near-empty (footer/sidebar only)').classes('text-xs text-gray-500 mb-2')
            
            ui.label('Additional CSS URLs (Optional)').classes('text-sm text-gray-600 mt-2 mb-1')
            ui.label('One URL per line. Use if extracted CSS is missing.').classes('text-xs text-gray-500 mb-2')
            self.extra_css_urls = ui.textarea(placeholder='https://example.com/css/custom.css\nhttps://cdn.example.com/styles.css').classes('w-full').props('outlined rows=4')
            if self.config.extra_css_urls:
                self.extra_css_urls.value = '\n'.join(self.config.extra_css_urls)
            
            # URL Filters
            ui.label('URL Filters (Regex)').classes('font-semibold text-lg mt-4 mb-2')
            with ui.row().classes('gap-4 w-full'):
                with ui.column().classes('flex-1'):
                    ui.label('Include Patterns').classes('text-sm mb-1')
                    self.include_patterns = ui.textarea(
                        placeholder='.*/api/.*\n.*/docs/.*'
                    ).classes('w-full').props('outlined rows=3')
                
                with ui.column().classes('flex-1'):
                    ui.label('Exclude Patterns').classes('text-sm mb-1')
                    self.exclude_patterns = ui.textarea(
                        placeholder='.*/login.*\n.*/admin.*'
                    ).classes('w-full').props('outlined rows=3')
            
            # URL Scope Control (NEW)
            ui.separator().classes('my-4')
            ui.label('URL Scope Control 🎯').classes('font-semibold text-lg mb-2')
            ui.label('Prevent scope creep by limiting which URLs are crawled').classes('text-sm text-gray-600 mb-3')
            
            self.strict_base_path_cb = ui.checkbox(
                'Strict Mode: Only crawl URLs under start URL path (recommended)', 
                value=self.config.strict_base_path
            ).classes('mb-2')
            self.strict_base_path_cb.on('change', lambda e: setattr(self.config, 'strict_base_path', e.value))
            ui.label('Example: Start=/module.html → Only crawl /module/*').classes('text-xs text-gray-500 ml-6 mb-3')
            
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.label('Parent Levels:').classes('text-sm')
                self.parent_levels_input = ui.number('', value=self.config.parent_levels, min=0, max=5).classes('w-20')
                self.parent_levels_input.on('change', lambda e: setattr(self.config, 'parent_levels', int(e.value)))
                ui.label('(0=strict, 1=one level up, etc.)').classes('text-xs text-gray-500')
            
            with ui.row().classes('gap-4 w-full'):
                with ui.column().classes('flex-1'):
                    ui.label('URLs must contain (one per line, OR logic):').classes('text-sm mb-1')
                    self.url_must_contain = ui.textarea(
                        placeholder='/module\n/documentation'
                    ).classes('w-full font-mono text-sm').props('outlined rows=2')
                
                with ui.column().classes('flex-1'):
                    ui.label('URLs must NOT contain (one per line):').classes('text-sm mb-1')
                    self.url_must_not_contain = ui.textarea(
                        placeholder='/aufgaben\n/rollen\n/search'
                    ).classes('w-full font-mono text-sm').props('outlined rows=2')
    
    def _toggle_css_selectors(self, strategy):
        """Show/hide CSS selectors based on strategy"""
        self.css_textarea.visible = (strategy == 'CSS Selectors')
    
    def _update_max_pages(self, value):
        """Update max pages value"""
        self.config.max_pages = int(value)
        self.max_pages_label.text = str(int(value))
    
    def _update_depth(self, value):
        """Update crawl depth value"""
        self.config.crawl_depth = int(value)
        self.depth_label.text = str(int(value))
    
    def _update_form_values(self):
        """Update form fields with current config values"""
        # Update URL - force update auch wenn vorher gesetzt
        if self.url_input:
            if self.config.url:
                self.url_input.value = self.config.url
                self.url_input.update()  # Force UI update
        
        if self.output_input:
            if self.config.output_name:
                self.output_input.value = self.config.output_name
                self.output_input.update()  # Force UI update
        if self.max_pages_slider:
            self.max_pages_slider.value = self.config.max_pages
            self.max_pages_label.text = str(self.config.max_pages)
        if self.depth_slider:
            self.depth_slider.value = self.config.crawl_depth
            self.depth_label.text = str(self.config.crawl_depth)
        
        # Update navigation strategy dropdown
        if hasattr(self, 'strategy_select') and self.strategy_select:
            self.strategy_select.value = self.config.nav_strategy
            # Show/hide GitHub options
            if hasattr(self, 'github_options'):
                self.github_options.visible = (self.config.nav_strategy == 'github')
        
        # Update GitHub-specific fields
        if hasattr(self, 'github_extensions_input') and self.github_extensions_input:
            self.github_extensions_input.value = ', '.join(self.config.github_extensions)
        if hasattr(self, 'github_max_files') and self.github_max_files:
            self.github_max_files.value = self.config.github_max_files
        
        # Update Advanced Options - HTML Formatting
        if hasattr(self, 'enhanced_html_cb') and self.enhanced_html_cb:
            self.enhanced_html_cb.value = self.config.enhanced_html_formatting
        if hasattr(self, 'fallback_css_cb') and self.fallback_css_cb:
            self.fallback_css_cb.value = self.config.use_fallback_css
        if hasattr(self, 'inline_standalone_cb') and self.inline_standalone_cb:
            self.inline_standalone_cb.value = self.config.inline_standalone
        if hasattr(self, 'min_content_length_input') and self.min_content_length_input:
            self.min_content_length_input.value = self.config.min_content_length
        if hasattr(self, 'extra_css_urls') and self.extra_css_urls:
            if self.config.extra_css_urls:
                self.extra_css_urls.value = '\n'.join(self.config.extra_css_urls)
        
        # Update URL Filters
        if hasattr(self, 'include_patterns') and self.include_patterns:
            if self.config.include_patterns:
                self.include_patterns.value = '\n'.join(self.config.include_patterns)
        if hasattr(self, 'exclude_patterns') and self.exclude_patterns:
            if self.config.exclude_patterns:
                self.exclude_patterns.value = '\n'.join(self.config.exclude_patterns)
        
        # Update URL Scope Control (NEW)
        if hasattr(self, 'strict_base_path_cb') and self.strict_base_path_cb:
            self.strict_base_path_cb.value = self.config.strict_base_path
        if hasattr(self, 'parent_levels_input') and self.parent_levels_input:
            self.parent_levels_input.value = self.config.parent_levels
        if hasattr(self, 'url_must_contain') and self.url_must_contain:
            if self.config.url_must_contain:
                self.url_must_contain.value = '\n'.join(self.config.url_must_contain)
        if hasattr(self, 'url_must_not_contain') and self.url_must_not_contain:
            if self.config.url_must_not_contain:
                self.url_must_not_contain.value = '\n'.join(self.config.url_must_not_contain)
    
    def _render_actions(self):
        """Render action buttons"""
        with ui.row().classes('w-full justify-between'):
            ui.button(
                'Validate Config',
                icon='check_circle',
                on_click=self._validate_config
            ).props('outline color=secondary size=lg')
            
            ui.button(
                'Start Crawl',
                icon='rocket_launch',
                on_click=self._start_crawl
            ).props('color=primary size=lg unelevated')
    
    def _validate_config(self):
        """Validate the configuration"""
        errors = []
        
        if not self.config.url or not self.config.url.startswith('http'):
            errors.append('❌ Invalid URL - must start with http:// or https://')
        
        if not self.config.output_name or not self.config.output_name.endswith('.docx'):
            errors.append('❌ Output filename must end with .docx')
        
        if self.config.max_pages < 1 or self.config.max_pages > 1000:
            errors.append('❌ Max pages must be between 1 and 1000')
        
        if errors:
            with ui.dialog() as dialog, ui.card():
                ui.label('Configuration Errors').classes('text-lg font-bold mb-4')
                for error in errors:
                    ui.label(error).classes('text-red-600 mb-2')
                ui.button('Close', on_click=dialog.close).props('color=negative')
            dialog.open()
        else:
            ui.notify('✅ Configuration is valid! Ready to crawl.', type='positive')
    
    def _start_crawl(self):
        """Start the crawl"""
        # Read current values from input fields BEFORE validation
        if self.url_input:
            self.config.url = self.url_input.value
        if self.output_input:
            self.config.output_name = self.output_input.value
        if self.max_pages_slider:
            self.config.max_pages = int(self.max_pages_slider.value)
        if self.depth_slider:
            self.config.crawl_depth = int(self.depth_slider.value)
        
        # Read GitHub-specific options if GitHub strategy is selected
        if self.config.nav_strategy == 'github':
            if hasattr(self, 'github_extensions_input') and self.github_extensions_input.value:
                # Parse comma-separated extensions
                exts = [e.strip() for e in self.github_extensions_input.value.split(',') if e.strip()]
                self.config.github_extensions = exts
            if hasattr(self, 'github_max_files') and self.github_max_files.value:
                self.config.github_max_files = int(self.github_max_files.value)
        
        # Read navigation strategy from dropdown
        if hasattr(self, 'strategy_select') and self.strategy_select:
            self.config.nav_strategy = self.strategy_select.value
        
        # Read checkbox values
        if hasattr(self, 'enhanced_html_cb'):
            self.config.enhanced_html_formatting = self.enhanced_html_cb.value
            print(f"DEBUG: enhanced_html_formatting = {self.config.enhanced_html_formatting}")
        if hasattr(self, 'fallback_css_cb'):
            self.config.use_fallback_css = self.fallback_css_cb.value
            print(f"DEBUG: use_fallback_css = {self.config.use_fallback_css}")
        if hasattr(self, 'inline_standalone_cb'):
            self.config.inline_standalone = self.inline_standalone_cb.value
            print(f"DEBUG: inline_standalone = {self.config.inline_standalone}")
        if hasattr(self, 'min_content_length_input'):
            self.config.min_content_length = int(self.min_content_length_input.value) if self.min_content_length_input.value else 0
            print(f"DEBUG: min_content_length = {self.config.min_content_length}")
        
        if not self.config.is_valid():
            ui.notify('Please fix configuration errors first', type='negative')
            return
        
        # Parse URL filters
        if self.include_patterns and self.include_patterns.value:
            self.config.include_patterns = [
                p.strip() for p in self.include_patterns.value.split('\n') if p.strip()
            ]
        
        if self.exclude_patterns and self.exclude_patterns.value:
            self.config.exclude_patterns = [
                p.strip() for p in self.exclude_patterns.value.split('\n') if p.strip()
            ]
        
        # Parse URL Scope Control (CRITICAL FIX: Add strict_base_path and parent_levels)
        if hasattr(self, 'strict_base_path_cb'):
            self.config.strict_base_path = self.strict_base_path_cb.value
            print(f"DEBUG: strict_base_path = {self.config.strict_base_path}")
        
        if hasattr(self, 'parent_levels_input'):
            self.config.parent_levels = int(self.parent_levels_input.value)
            print(f"DEBUG: parent_levels = {self.config.parent_levels}")
        
        if hasattr(self, 'url_must_contain') and self.url_must_contain and self.url_must_contain.value:
            self.config.url_must_contain = [
                p.strip() for p in self.url_must_contain.value.split('\n') if p.strip()
            ]
        
        if hasattr(self, 'url_must_not_contain') and self.url_must_not_contain and self.url_must_not_contain.value:
            self.config.url_must_not_contain = [
                p.strip() for p in self.url_must_not_contain.value.split('\n') if p.strip()
            ]
        
        # Parse extra CSS URLs
        if hasattr(self, 'extra_css_urls') and self.extra_css_urls and self.extra_css_urls.value:
            self.config.extra_css_urls = [
                u.strip() for u in self.extra_css_urls.value.split('\n') if u.strip()
            ]
        
        # Start real crawl via crawler service
        try:
            result = self.crawler_service.start_crawl(self.config.to_dict())
            crawl_id = result['crawl_id']
            ui.notify(f'Crawl started! ID: {crawl_id}', type='positive')
            ui.navigate.to(f'/crawl/progress/{crawl_id}')
        except Exception as e:
            ui.notify(f'Failed to start crawl: {str(e)}', type='negative')
