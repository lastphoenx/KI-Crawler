"""
Router configuration for all pages
"""

from nicegui import ui
from pages.dashboard import DashboardPage
from pages.new_crawl import NewCrawlPage
from pages.progress_monitor import ProgressMonitorPage
from pages.results import ResultsPage
from components.header import render_header
from components.footer import render_footer


def setup_routes():
    """Register all application routes"""
    
    @ui.page('/')
    def home():
        """Dashboard/Home page"""
        render_header()
        with ui.column().classes('w-full'):
            DashboardPage().render()
        render_footer()
    
    @ui.page('/new')
    def redirect_new():
        """Redirect /new to /crawl/new"""
        ui.navigate.to('/crawl/new')
    
    @ui.page('/crawl/new')
    def new_crawl(url: str = None, template: str = None):
        """New crawl configuration page"""
        render_header()
        with ui.column().classes('w-full'):
            NewCrawlPage(prefill_url=url, template=template).render()
        render_footer()
    
    @ui.page('/crawl/progress/{crawl_id}')
    def crawl_progress(crawl_id: str):
        """Crawl progress monitoring page"""
        render_header()
        with ui.column().classes('w-full'):
            ProgressMonitorPage(crawl_id).render()
        render_footer()
    
    @ui.page('/crawl/results/{crawl_id}')
    def crawl_results(crawl_id: str):
        """Crawl results page"""
        render_header()
        with ui.column().classes('w-full'):
            ResultsPage(crawl_id).render()
        render_footer()
    
    @ui.page('/history')
    def history():
        """Crawl history page"""
        from services.crawl_state_manager import CrawlStateManager
        
        render_header()
        with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-4'):
            # Header row
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('Crawl History').classes('text-3xl font-bold')
                
                # Delete all button
                ui.button(
                    '🗑️ Clear All',
                    icon='delete_sweep',
                    on_click=lambda: _confirm_delete_all()
                ).props('color=negative').classes('self-end')
            
            # Get all recent crawls
            state_manager = CrawlStateManager()
            recent = state_manager.get_recent_crawls(50)
            
            if not recent:
                ui.label('📭 No crawl history yet').classes('text-xl text-gray-600 p-8')
                ui.label('Start your first crawl from the dashboard!').classes('text-gray-500')
            else:
                ui.label(f'Total: {len(recent)} crawls').classes('text-sm text-gray-600 mb-2')
                
                for state in recent:
                    # Use pages_crawled, but fallback to actual data if it's 0
                    actual_pages = state.pages_crawled
                    if actual_pages == 0:
                        # Fallback: use length of crawled_pages dict or current_page
                        if hasattr(state, 'crawled_pages') and state.crawled_pages:
                            actual_pages = len(state.crawled_pages)
                        elif state.current_page > 0:
                            actual_pages = state.current_page
                    
                    with ui.card().classes('w-full p-6 hover-lift mb-4'):
                        with ui.column().classes('gap-2'):
                            # Header row
                            with ui.row().classes('w-full justify-between items-start'):
                                with ui.column().classes('flex-1'):
                                    ui.label(state.config.get('url', 'Unknown URL')).classes('text-lg font-bold')
                                    ui.label(f'Started: {state.start_time.strftime("%Y-%m-%d %H:%M:%S")}').classes('text-sm text-gray-600')
                                
                                # Status badge
                                status_color = 'green' if state.status == 'completed' else 'orange' if state.status == 'running' else 'red'
                                ui.badge(state.status.upper(), color=status_color)
                            
                            # Stats row
                            with ui.row().classes('gap-6 mt-2'):
                                ui.label(f'📄 {actual_pages} pages').classes('text-sm')
                                ui.label(f'⏱️ {state.get_duration():.1f}s').classes('text-sm')
                                if state.errors > 0:
                                    ui.label(f'❌ {state.errors} errors').classes('text-sm text-red-600')
                            
                            # Actions
                            with ui.row().classes('gap-2 mt-4'):
                                ui.button(
                                    'View Details',
                                    icon='visibility',
                                    on_click=lambda id=state.crawl_id: ui.navigate.to(f'/crawl/results/{id}')
                                ).props('size=sm')
                                
                                if state.output_path:
                                    ui.button(
                                        'Download',
                                        icon='download',
                                        on_click=lambda path=state.output_path: _download_from_history(path)
                                    ).props('size=sm outline')
                                
                                # Delete button
                                ui.button(
                                    '',
                                    icon='delete',
                                    on_click=lambda id=state.crawl_id, url=state.config.get('url', ''): _confirm_delete_crawl(id, url)
                                ).props('size=sm flat').classes('text-red-600')
        
        render_footer()
    
    def _download_from_history(file_path):
        """Download file from history"""
        import subprocess
        from pathlib import Path
        if file_path and Path(file_path).exists():
            subprocess.run(['explorer', '/select,', str(file_path)])
        else:
            ui.notify('File not found', type='negative')
    
    def _confirm_delete_crawl(crawl_id: str, url: str):
        """Confirm deletion of a single crawl"""
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
            with ui.column().classes('gap-4 p-6'):
                ui.label('Delete Crawl?').classes('text-xl font-bold')
                ui.label(f'URL: {url}').classes('text-sm text-gray-600')
                ui.label('This action cannot be undone.').classes('text-sm text-red-600 font-semibold')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).props('outline')
                    ui.button('Delete', on_click=lambda: [_delete_crawl(crawl_id), dialog.close()]).classes('bg-red-600 text-white')
        
        dialog.open()
    
    def _confirm_delete_all():
        """Confirm deletion of all crawls"""
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
            with ui.column().classes('gap-4 p-6'):
                ui.label('Clear All Crawls?').classes('text-xl font-bold')
                ui.label('This will delete all history entries and their files.').classes('text-sm text-gray-600')
                ui.label('This action cannot be undone.').classes('text-sm text-red-600 font-semibold')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).props('outline')
                    ui.button('Clear All', on_click=lambda: [_delete_all_crawls(), dialog.close()]).classes('bg-red-600 text-white')
        
        dialog.open()
    
    def _delete_crawl(crawl_id: str):
        """Delete a single crawl"""
        from services.crawl_state_manager import CrawlStateManager
        state_manager = CrawlStateManager()
        
        if state_manager.delete_crawl(crawl_id):
            ui.notify('✅ Crawl deleted', type='positive')
            ui.navigate.reload()
        else:
            ui.notify('❌ Failed to delete crawl', type='negative')
    
    def _delete_all_crawls():
        """Delete all crawls"""
        from services.crawl_state_manager import CrawlStateManager
        state_manager = CrawlStateManager()
        
        if state_manager.delete_all_crawls():
            ui.notify('✅ All crawls deleted', type='positive')
            ui.navigate.reload()
        else:
            ui.notify('❌ Failed to delete crawls', type='negative')
    
    @ui.page('/settings')
    def settings():
        """Settings page"""
        render_header()
        with ui.column().classes('w-full'):
            ui.label('Settings').classes('text-3xl font-bold p-8')
            ui.label('🚧 Coming soon...').classes('text-xl text-gray-600 p-8')
        render_footer()
    
    @ui.page('/templates')
    def templates():
        """Template gallery page"""
        from pages.templates import TemplatesPage
        render_header()
        templates_page = TemplatesPage()
        templates_page.render()
        render_footer()
