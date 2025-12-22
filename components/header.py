"""
Header component with navigation
"""

from nicegui import ui


def render_header():
    """Render the application header with navigation"""
    
    with ui.header().classes('bg-indigo-600 text-white shadow-lg'):
        with ui.row().classes('w-full max-w-7xl mx-auto items-center justify-between p-4'):
            # Logo & Brand
            with ui.link(target='/').classes('no-underline flex items-center gap-3'):
                ui.label('🕷️').classes('text-3xl')
                ui.label('Web Crawler Pro').classes('text-xl font-bold text-white')
            
            # Navigation Menu
            with ui.row().classes('gap-6 items-center'):
                ui.link('Dashboard', target='/')\
                    .classes('text-white hover:text-indigo-200 transition-colors')
                
                ui.link('New Crawl', target='/crawl/new')\
                    .classes('text-white hover:text-indigo-200 transition-colors')
                
                ui.link('Templates', target='/templates')\
                    .classes('text-white hover:text-indigo-200 transition-colors')
                
                ui.link('History', target='/history')\
                    .classes('text-white hover:text-indigo-200 transition-colors')
                
                ui.link('Settings', target='/settings')\
                    .classes('text-white hover:text-indigo-200 transition-colors')
            
            # User Menu (future)
            with ui.button(icon='account_circle').props('flat round color=white'):
                with ui.menu():
                    ui.menu_item('Profile', lambda: ui.notify('Profile'))
                    ui.menu_item('About', lambda: ui.notify('Web Crawler Pro v2.0'))
                    ui.separator()
                    ui.menu_item('Logout', lambda: ui.notify('Logged out'))
