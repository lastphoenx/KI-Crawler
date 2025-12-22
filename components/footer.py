"""
Footer component
"""

from nicegui import ui


def render_footer():
    """Render the application footer"""
    
    with ui.footer().classes('bg-gray-100 border-t border-gray-200'):
        with ui.row().classes('w-full max-w-7xl mx-auto justify-between p-4 text-sm text-gray-600'):
            ui.label('© 2025 Web Crawler Pro - Version 2.0')
            
            with ui.row().classes('gap-4'):
                ui.link('Documentation', '#').classes('text-gray-600 hover:text-indigo-600')
                ui.link('Support', '#').classes('text-gray-600 hover:text-indigo-600')
                ui.link('GitHub', '#').classes('text-gray-600 hover:text-indigo-600')
