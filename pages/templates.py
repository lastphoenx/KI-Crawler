"""
Templates management page
"""

from nicegui import ui
from services.template_service import TemplateService


class TemplatesPage:
    """Template gallery and management page"""
    
    def __init__(self):
        self.template_service = TemplateService()
        self.selected_template = None
        self.edit_mode = False
    
    def render(self):
        """Render the templates page"""
        with ui.column().classes('w-full gap-6 p-8'):
            # Header
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-1'):
                    ui.label('📋 Templates').classes('text-3xl font-bold')
                    ui.label('Manage and customize crawl templates').classes('text-gray-600')
                
                ui.button('➕ Create Custom Template', on_click=self._create_template)\
                    .classes('bg-indigo-600 text-white')
            
            ui.separator()
            
            # Template Grid
            self._render_template_grid()
    
    def _render_template_grid(self):
        """Render template cards in a grid"""
        templates = self.template_service.get_all_templates()
        
        with ui.row().classes('w-full gap-6 flex-wrap'):
            for template in templates:
                self._render_template_card(template)
    
    def _render_template_card(self, template):
        """Render a single template card"""
        with ui.card().classes('hover-lift cursor-pointer border border-gray-200')\
                .style('min-width: 300px; max-width: 400px'):
            with ui.column().classes('gap-4 p-6'):
                # Header
                with ui.row().classes('w-full items-start justify-between'):
                    with ui.row().classes('items-center gap-3'):
                        ui.label(template['icon']).classes('text-4xl')
                        with ui.column().classes('gap-1'):
                            ui.label(template['name']).classes('font-bold text-xl')
                            ui.label(template['description']).classes('text-sm text-gray-600')
                    
                    # Edit button for custom templates
                    if template['id'].startswith('custom_'):
                        ui.button(icon='edit', on_click=lambda t=template: self._edit_template(t))\
                            .props('flat round size=sm').classes('text-gray-500')
                
                ui.separator()
                
                # Configuration Preview
                config = template.get('config', {})
                with ui.column().classes('gap-2'):
                    ui.label('Configuration:').classes('text-sm font-semibold text-gray-700')
                    
                    # Show key settings
                    settings = []
                    if 'nav_strategy' in config:
                        settings.append(f"Strategy: {config['nav_strategy']}")
                    if 'max_pages' in config:
                        settings.append(f"Max Pages: {config['max_pages']}")
                    if 'github_extensions' in config:
                        ext_count = len(config['github_extensions'])
                        settings.append(f"File Types: {ext_count} extensions")
                    
                    for setting in settings[:5]:  # Show max 5 settings
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('check_circle').classes('text-green-600 text-sm')
                            ui.label(setting).classes('text-sm text-gray-700')
                
                ui.separator()
                
                # Actions
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.row().classes('gap-2'):
                        ui.button('Use Template', on_click=lambda t=template: self._use_template(t))\
                            .classes('bg-indigo-600 text-white')
                        ui.button('View Details', on_click=lambda t=template: self._view_details(t))\
                            .props('outline').classes('text-indigo-600')
                    
                    # Delete for custom templates
                    if template['id'].startswith('custom_'):
                        ui.button(icon='delete', on_click=lambda t=template: self._delete_template(t))\
                            .props('flat round size=sm').classes('text-red-600')
    
    def _use_template(self, template):
        """Navigate to new crawl with this template pre-selected"""
        # Navigate to new crawl page with template ID as URL parameter
        from nicegui import ui as nicegui_ui
        template_id = template.get('id', '')
        nicegui_ui.navigate.to(f'/crawl/new?template={template_id}')
    
    def _view_details(self, template):
        """Show template details in a dialog"""
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl'):
            with ui.column().classes('gap-4 p-6'):
                # Header
                with ui.row().classes('items-center gap-3 mb-4'):
                    ui.label(template['icon']).classes('text-5xl')
                    with ui.column():
                        ui.label(template['name']).classes('text-2xl font-bold')
                        ui.label(template['description']).classes('text-gray-600')
                
                ui.separator()
                
                # Full configuration
                config = template.get('config', {})
                ui.label('Full Configuration:').classes('text-lg font-semibold mb-2')
                
                with ui.column().classes('gap-2 bg-gray-50 p-4 rounded'):
                    for key, value in config.items():
                        with ui.row().classes('items-start gap-2'):
                            ui.label(f'{key}:').classes('font-mono text-sm font-semibold min-w-32')
                            if isinstance(value, list):
                                ui.label(f'{len(value)} items').classes('font-mono text-sm text-gray-700')
                            else:
                                ui.label(str(value)).classes('font-mono text-sm text-gray-700')
                
                # Actions
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Close', on_click=dialog.close).props('outline')
                    ui.button('Use Template', on_click=lambda: [dialog.close(), self._use_template(template)])\
                        .classes('bg-indigo-600 text-white')
        
        dialog.open()
    
    def _create_template(self):
        """Show dialog to create a new custom template"""
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl'):
            with ui.column().classes('gap-4 p-6'):
                ui.label('Create Custom Template').classes('text-2xl font-bold mb-4')
                
                # Form fields
                name_input = ui.input('Template Name', placeholder='My Custom Template')\
                    .classes('w-full')
                description_input = ui.input('Description', placeholder='Description of what this template does')\
                    .classes('w-full')
                
                ui.separator()
                
                ui.label('Configuration').classes('text-lg font-semibold')
                
                # Basic Settings
                with ui.column().classes('gap-3'):
                    url_input = ui.input('Default URL (optional)', placeholder='https://...')\
                        .classes('w-full')
                    
                    filename_input = ui.input('Output Filename (optional)', 
                                             placeholder='documentation.docx',
                                             value='documentation.docx')\
                        .classes('w-full')
                    
                    strategy_select = ui.select(
                        ['pcloud', 'generic', 'github'],
                        label='Navigation Strategy',
                        value='pcloud'
                    ).classes('w-full')
                    
                    max_pages_input = ui.number('Max Pages', value=100, min=1, max=1000)\
                        .classes('w-full')
                
                # Advanced Options (Expandable)
                with ui.expansion('⚙️ Advanced Options', icon='settings').classes('w-full'):
                    with ui.column().classes('gap-3 pt-2'):
                        # Document Options
                        ui.label('Document Options').classes('font-semibold text-sm')
                        include_toc = ui.checkbox('Include Table of Contents', value=True)
                        include_error_log = ui.checkbox('Include Error Log', value=True)
                        enhanced_html = ui.checkbox('Enhanced HTML Formatting', value=False)
                        use_fallback_css = ui.checkbox('Use Fallback CSS', value=True)
                        inline_standalone = ui.checkbox('Generate Standalone HTML (single-file)', value=False)
                        ui.label('Creates portable HTML with inline assets').classes('text-xs text-gray-500')
                        
                        ui.separator()
                        
                        # JavaScript Rendering
                        ui.label('JavaScript Rendering').classes('font-semibold text-sm')
                        js_enabled = ui.checkbox('Enable JavaScript Rendering', value=True)
                        js_headless = ui.checkbox('Run Headless Browser', value=True)
                        js_timeout = ui.number('JS Timeout (ms)', value=30000, min=5000, max=120000)
                        
                        ui.separator()
                        
                        # Crawler Options
                        ui.label('Crawler Options').classes('font-semibold text-sm')
                        max_retries = ui.number('Max Retries', value=3, min=1, max=10)
                        timeout_seconds = ui.number('Timeout (seconds)', value=10, min=5, max=60)
                        
                        ui.separator()
                        
                        # Listing Filter
                        ui.label('Page Filtering').classes('font-semibold text-sm')
                        include_listing_pages = ui.checkbox('Include Listing Pages', value=False)
                        
                        # Include patterns
                        ui.label('Include Patterns (regex, one per line)').classes('text-xs text-gray-600')
                        include_patterns = ui.textarea(
                            placeholder='.*/methods/.*\n.*/structures/.*'
                        ).classes('w-full font-mono text-sm').props('rows=3')
                        
                        # Exclude patterns
                        ui.label('Exclude Patterns (regex, one per line)').classes('text-xs text-gray-600 mt-2')
                        exclude_patterns = ui.textarea(
                            placeholder='.*/404.*\n.*/search.*'
                        ).classes('w-full font-mono text-sm').props('rows=3')
                        
                        ui.separator()
                        
                        # URL Scope Control (NEW)
                        ui.label('URL Scope Control 🎯').classes('font-semibold text-sm')
                        ui.label('Prevent scope creep by limiting which URLs are crawled').classes('text-xs text-gray-500')
                        
                        strict_base_path = ui.checkbox(
                            'Strict Mode: Only crawl URLs under start URL path (recommended)', 
                            value=True
                        ).classes('text-sm')
                        ui.label('Example: Start=/module.html → Only crawl /module/*').classes('text-xs text-gray-500 ml-6')
                        
                        with ui.row().classes('items-center gap-2 mt-2'):
                            ui.label('Parent Levels:').classes('text-sm')
                            parent_levels = ui.number('', value=0, min=0, max=5).classes('w-20')
                            ui.label('(0=strict, 1=one level up, etc.)').classes('text-xs text-gray-500')
                        
                        # Must contain
                        ui.label('URLs must contain (one per line, OR logic):').classes('text-xs text-gray-600 mt-2')
                        url_must_contain = ui.textarea(
                            placeholder='/module\n/documentation'
                        ).classes('w-full font-mono text-sm').props('rows=2')
                        
                        # Must NOT contain
                        ui.label('URLs must NOT contain (one per line):').classes('text-xs text-gray-600 mt-2')
                        url_must_not_contain = ui.textarea(
                            placeholder='/aufgaben\n/rollen\n/search'
                        ).classes('w-full font-mono text-sm').props('rows=2')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).props('outline')
                    ui.button('Create', on_click=lambda: self._save_custom_template(
                        dialog,
                        name_input.value,
                        description_input.value,
                        url_input.value,
                        filename_input.value,
                        strategy_select.value,
                        max_pages_input.value,
                        # Advanced options
                        include_toc.value,
                        include_error_log.value,
                        enhanced_html.value,
                        use_fallback_css.value,
                        inline_standalone.value,
                        js_enabled.value,
                        js_headless.value,
                        js_timeout.value,
                        max_retries.value,
                        timeout_seconds.value,
                        include_listing_pages.value,
                        include_patterns.value,
                        exclude_patterns.value,
                        # URL Scope Control (NEW)
                        strict_base_path.value,
                        parent_levels.value,
                        url_must_contain.value,
                        url_must_not_contain.value
                    )).classes('bg-indigo-600 text-white')
        
        dialog.open()
    
    def _save_custom_template(self, dialog, name, description, url, filename,
                             strategy, max_pages,
                             include_toc, include_error_log, enhanced_html, use_fallback_css, inline_standalone,
                             js_enabled, js_headless, js_timeout, max_retries, timeout_seconds,
                             include_listing_pages, include_patterns_text, exclude_patterns_text,
                             strict_base_path, parent_levels, url_must_contain_text, url_must_not_contain_text):
        """Save a new custom template"""
        if not name:
            ui.notify('Please provide a template name', type='warning')
            return
        
        # Parse patterns from textarea
        include_patterns = [p.strip() for p in include_patterns_text.split('\n') if p.strip()] if include_patterns_text else []
        exclude_patterns = [p.strip() for p in exclude_patterns_text.split('\n') if p.strip()] if exclude_patterns_text else []
        
        # Parse URL scope patterns
        url_must_contain = [p.strip() for p in url_must_contain_text.split('\n') if p.strip()] if url_must_contain_text else []
        url_must_not_contain = [p.strip() for p in url_must_not_contain_text.split('\n') if p.strip()] if url_must_not_contain_text else []
        
        # Create template object
        import uuid
        template_id = f'custom_{uuid.uuid4().hex[:8]}'
        
        new_template = {
            'id': template_id,
            'name': name,
            'description': description or 'Custom template',
            'icon': '🔧',
            'config': {
                # Crawler
                'nav_strategy': strategy,
                'max_pages': int(max_pages) if max_pages else 100,
                'max_retries': int(max_retries) if max_retries else 3,
                'timeout_seconds': int(timeout_seconds) if timeout_seconds else 10,
                
                # URL Scope Control (NEW)
                'strict_base_path': strict_base_path,
                'parent_levels': int(parent_levels) if parent_levels else 0,
                'url_must_contain': url_must_contain,
                'url_must_not_contain': url_must_not_contain,
                
                # JavaScript Rendering
                'javascript_rendering': {
                    'enabled': js_enabled,
                    'headless': js_headless,
                    'timeout': int(js_timeout) if js_timeout else 30000,
                    'auto_detect': True
                },
                
                # Document
                'document': {
                    'include_toc': include_toc,
                    'include_error_log': include_error_log,
                    'enhanced_html_formatting': enhanced_html,
                    'use_fallback_css': use_fallback_css,
                    'inline_standalone': inline_standalone,
                    'listing_filter': {
                        'include_listing_pages': include_listing_pages,
                        'force_include_patterns': include_patterns,
                        'force_exclude_patterns': exclude_patterns
                    }
                }
            }
        }
        
        # Add optional fields
        if url:
            new_template['config']['entry_url'] = url
        if filename:
            new_template['config']['output_name'] = filename
        
        # Save template
        from services.template_service import TemplateService
        template_service = TemplateService()
        if template_service.save_template(new_template):
            ui.notify(f'✅ Template "{name}" created and saved!', type='positive')
            dialog.close()
            ui.navigate.reload()
        else:
            ui.notify('❌ Failed to save template', type='negative')
    
    def _edit_template(self, template):
        """Edit an existing custom template"""
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl'):
            with ui.column().classes('gap-4 p-6'):
                ui.label('Edit Template').classes('text-2xl font-bold mb-4')
                
                # Form fields
                name_input = ui.input('Template Name', value=template.get('name', ''))\
                    .classes('w-full')
                description_input = ui.input('Description', value=template.get('description', ''))\
                    .classes('w-full')
                
                ui.separator()
                
                ui.label('Configuration').classes('text-lg font-semibold')
                
                config = template.get('config', {})
                doc_config = config.get('document', {})
                listing_filter = doc_config.get('listing_filter', {})
                js_config = config.get('javascript_rendering', {})
                
                # Basic Settings
                with ui.column().classes('gap-3'):
                    url_input = ui.input(
                        'Default URL (optional)', 
                        value=config.get('entry_url', ''),
                        placeholder='https://...'
                    ).classes('w-full')
                    
                    filename_input = ui.input(
                        'Output Filename (optional)',
                        value=config.get('output_name', 'documentation.docx'),
                        placeholder='documentation.docx'
                    ).classes('w-full')
                    
                    strategy_select = ui.select(
                        ['pcloud', 'generic', 'github'],
                        label='Navigation Strategy',
                        value=config.get('nav_strategy', 'pcloud')
                    ).classes('w-full')
                    
                    max_pages_input = ui.number(
                        'Max Pages', 
                        value=config.get('max_pages', 100), 
                        min=1, 
                        max=1000
                    ).classes('w-full')
                
                # Advanced Options (Expandable)
                with ui.expansion('⚙️ Advanced Options', icon='settings', value=True).classes('w-full'):
                    with ui.column().classes('gap-3 pt-2'):
                        # Document Options
                        ui.label('Document Options').classes('font-semibold text-sm')
                        include_toc = ui.checkbox('Include Table of Contents', 
                                                 value=doc_config.get('include_toc', True))
                        include_error_log = ui.checkbox('Include Error Log', 
                                                       value=doc_config.get('include_error_log', True))
                        enhanced_html = ui.checkbox('Enhanced HTML Formatting', 
                                                   value=doc_config.get('enhanced_html_formatting', False))
                        use_fallback_css = ui.checkbox('Use Fallback CSS', 
                                                      value=doc_config.get('use_fallback_css', True))
                        inline_standalone = ui.checkbox('Generate Standalone HTML', 
                                                       value=doc_config.get('inline_standalone', False))
                        ui.label('Single-file with inline assets (portable)').classes('text-xs text-gray-500')
                        
                        ui.separator()
                        
                        # JavaScript Rendering
                        ui.label('JavaScript Rendering').classes('font-semibold text-sm')
                        js_enabled = ui.checkbox('Enable JavaScript Rendering', 
                                                value=js_config.get('enabled', True))
                        js_headless = ui.checkbox('Run Headless Browser', 
                                                 value=js_config.get('headless', True))
                        js_timeout = ui.number('JS Timeout (ms)', 
                                             value=js_config.get('timeout', 30000), 
                                             min=5000, max=120000)
                        
                        ui.separator()
                        
                        # Crawler Options
                        ui.label('Crawler Options').classes('font-semibold text-sm')
                        max_retries = ui.number('Max Retries', 
                                              value=config.get('max_retries', 3), 
                                              min=1, max=10)
                        timeout_seconds = ui.number('Timeout (seconds)', 
                                                   value=config.get('timeout_seconds', 10), 
                                                   min=5, max=60)
                        
                        ui.separator()
                        
                        # Listing Filter
                        ui.label('Page Filtering').classes('font-semibold text-sm')
                        include_listing_pages = ui.checkbox('Include Listing Pages', 
                                                           value=listing_filter.get('include_listing_pages', False))
                        
                        # Include patterns
                        ui.label('Include Patterns (regex, one per line)').classes('text-xs text-gray-600')
                        include_patterns_list = listing_filter.get('force_include_patterns', [])
                        include_patterns = ui.textarea(
                            value='\n'.join(include_patterns_list),
                            placeholder='.*/methods/.*\n.*/structures/.*'
                        ).classes('w-full font-mono text-sm').props('rows=3')
                        
                        # Exclude patterns
                        ui.label('Exclude Patterns (regex, one per line)').classes('text-xs text-gray-600 mt-2')
                        exclude_patterns_list = listing_filter.get('force_exclude_patterns', [])
                        exclude_patterns = ui.textarea(
                            value='\n'.join(exclude_patterns_list),
                            placeholder='.*/404.*\n.*/search.*'
                        ).classes('w-full font-mono text-sm').props('rows=3')
                        
                        ui.separator()
                        
                        # URL Scope Control (NEW)
                        ui.label('URL Scope Control 🎯').classes('font-semibold text-sm')
                        ui.label('Prevent scope creep by limiting which URLs are crawled').classes('text-xs text-gray-500')
                        
                        strict_base_path = ui.checkbox(
                            'Strict Mode: Only crawl URLs under start URL path (recommended)', 
                            value=config.get('strict_base_path', True)
                        ).classes('text-sm')
                        ui.label('Example: Start=/module.html → Only crawl /module/*').classes('text-xs text-gray-500 ml-6')
                        
                        with ui.row().classes('items-center gap-2 mt-2'):
                            ui.label('Parent Levels:').classes('text-sm')
                            parent_levels = ui.number('', value=config.get('parent_levels', 0), min=0, max=5).classes('w-20')
                            ui.label('(0=strict, 1=one level up, etc.)').classes('text-xs text-gray-500')
                        
                        # Must contain
                        ui.label('URLs must contain (one per line, OR logic):').classes('text-xs text-gray-600 mt-2')
                        url_must_contain_list = config.get('url_must_contain', [])
                        url_must_contain = ui.textarea(
                            value='\n'.join(url_must_contain_list),
                            placeholder='/module\n/documentation'
                        ).classes('w-full font-mono text-sm').props('rows=2')
                        
                        # Must NOT contain
                        ui.label('URLs must NOT contain (one per line):').classes('text-xs text-gray-600 mt-2')
                        url_must_not_contain_list = config.get('url_must_not_contain', [])
                        url_must_not_contain = ui.textarea(
                            value='\n'.join(url_must_not_contain_list),
                            placeholder='/aufgaben\n/rollen\n/search'
                        ).classes('w-full font-mono text-sm').props('rows=2')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).props('outline')
                    ui.button('Save Changes', on_click=lambda: self._save_template_changes(
                        dialog,
                        template['id'],
                        name_input.value,
                        description_input.value,
                        url_input.value,
                        filename_input.value,
                        strategy_select.value,
                        max_pages_input.value,
                        # Advanced options
                        include_toc.value,
                        include_error_log.value,
                        enhanced_html.value,
                        use_fallback_css.value,
                        inline_standalone.value,
                        js_enabled.value,
                        js_headless.value,
                        js_timeout.value,
                        max_retries.value,
                        timeout_seconds.value,
                        include_listing_pages.value,
                        include_patterns.value,
                        exclude_patterns.value,
                        # URL Scope Control (NEW)
                        strict_base_path.value,
                        parent_levels.value,
                        url_must_contain.value,
                        url_must_not_contain.value
                    )).classes('bg-indigo-600 text-white')
        
        dialog.open()
    
    def _save_template_changes(self, dialog, template_id, name, description, url, filename,
                             strategy, max_pages,
                             include_toc, include_error_log, enhanced_html, use_fallback_css, inline_standalone,
                             js_enabled, js_headless, js_timeout, max_retries, timeout_seconds,
                             include_listing_pages, include_patterns_text, exclude_patterns_text,
                             strict_base_path, parent_levels, url_must_contain_text, url_must_not_contain_text):
        """Save template changes"""
        if not name:
            ui.notify('Please provide a template name', type='warning')
            return
        
        # Parse patterns from textarea
        include_patterns = [p.strip() for p in include_patterns_text.split('\n') if p.strip()] if include_patterns_text else []
        exclude_patterns = [p.strip() for p in exclude_patterns_text.split('\n') if p.strip()] if exclude_patterns_text else []
        
        # Parse URL scope patterns
        url_must_contain = [p.strip() for p in url_must_contain_text.split('\n') if p.strip()] if url_must_contain_text else []
        url_must_not_contain = [p.strip() for p in url_must_not_contain_text.split('\n') if p.strip()] if url_must_not_contain_text else []
        
        # Update template
        updated_template = {
            'id': template_id,
            'name': name,
            'description': description or 'Custom template',
            'icon': '🔧',
            'config': {
                # Crawler
                'nav_strategy': strategy,
                'max_pages': int(max_pages) if max_pages else 100,
                'max_retries': int(max_retries) if max_retries else 3,
                'timeout_seconds': int(timeout_seconds) if timeout_seconds else 10,
                
                # URL Scope Control (NEW)
                'strict_base_path': strict_base_path,
                'parent_levels': int(parent_levels) if parent_levels else 0,
                'url_must_contain': url_must_contain,
                'url_must_not_contain': url_must_not_contain,
                
                # JavaScript Rendering
                'javascript_rendering': {
                    'enabled': js_enabled,
                    'headless': js_headless,
                    'timeout': int(js_timeout) if js_timeout else 30000,
                    'auto_detect': True
                },
                
                # Document
                'document': {
                    'include_toc': include_toc,
                    'include_error_log': include_error_log,
                    'enhanced_html_formatting': enhanced_html,
                    'use_fallback_css': use_fallback_css,
                    'inline_standalone': inline_standalone,
                    'listing_filter': {
                        'include_listing_pages': include_listing_pages,
                        'force_include_patterns': include_patterns,
                        'force_exclude_patterns': exclude_patterns
                    }
                }
            }
        }
        
        # Add optional fields
        if url:
            updated_template['config']['entry_url'] = url
        if filename:
            updated_template['config']['output_name'] = filename
        
        # Save template
        from services.template_service import TemplateService
        template_service = TemplateService()
        if template_service.save_template(updated_template):
            ui.notify(f'✅ Template "{name}" updated!', type='positive')
            dialog.close()
            ui.navigate.reload()
        else:
            ui.notify('❌ Failed to save template', type='negative')
    
    def _delete_template(self, template):
        """Delete a custom template"""
        with ui.dialog() as dialog, ui.card():
            with ui.column().classes('gap-4 p-6'):
                ui.label(f'Delete "{template["name"]}"?').classes('text-xl font-bold')
                ui.label('This action cannot be undone.').classes('text-gray-600')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).props('outline')
                    ui.button('Delete', on_click=lambda: self._confirm_delete(template, dialog)).classes('bg-red-600 text-white')
        
        dialog.open()
    
    def _confirm_delete(self, template, dialog):
        """Confirm and execute template deletion"""
        from services.template_service import TemplateService
        template_service = TemplateService()
        
        if template_service.delete_template(template['id']):
            ui.notify(f'✅ Deleted "{template["name"]}"', type='positive')
            dialog.close()
            # Refresh page to show updated list
            ui.navigate.reload()
        else:
            ui.notify('❌ Cannot delete built-in templates', type='negative')
            dialog.close()
