"""
Progress Monitor Page - Real-time crawl progress tracking
"""

from nicegui import ui
import asyncio
from datetime import datetime
from services.crawl_state_manager import CrawlStateManager
from services.crawler_service import CrawlerService


class ProgressMonitorPage:
    """Real-time progress monitoring for active crawls"""
    
    def __init__(self, crawl_id: str):
        self.crawl_id = crawl_id
        self.state_manager = CrawlStateManager()
        self.crawler_service = CrawlerService()
        self.is_running = True
        
        # UI references
        self.progress_bar = None
        self.status_text = None
        self.pages_metric = None
        self.errors_metric = None
        self.speed_metric = None
        self.eta_metric = None
        self.log_container = None
        self.auto_scroll_checkbox = None
        self.preview_label = None
        self.chart_data = []
        self.results_button_container = None
        
        # Last log count for incremental updates
        self.last_log_count = 0
        self.auto_scroll_enabled = True
    
    def render(self):
        """Render the progress monitor page"""
        with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
            # Header
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('Crawling in Progress...').classes('text-3xl font-bold')
                
                with ui.row().classes('gap-2'):
                    ui.button(
                        icon='stop',
                        on_click=self._stop_crawl
                    ).props('color=negative outline').tooltip('Stop Crawl')
            
            # Progress Section
            self._render_progress()
            
            # Metrics
            self._render_metrics()
            
            # Activity Log
            self._render_activity_log()
            
            # Page Preview
            self._render_preview()
            
            # Results button (hidden initially, shown when complete)
            self.results_button_container = ui.row().classes('w-full justify-center mt-6')
            self.results_button_container.visible = False
        
        # Start monitoring
        ui.timer(0.1, self._start_monitoring, once=True)
    
    def _render_progress(self):
        """Render progress bar"""
        with ui.card().classes('w-full p-6'):
            ui.label('Overall Progress').classes('text-lg font-semibold mb-4')
            
            self.progress_bar = ui.linear_progress(
                value=0,
                show_value=True
            ).classes('h-6')
            
            self.status_text = ui.label('Initializing...').classes('text-sm text-gray-600 mt-2')
    
    def _render_metrics(self):
        """Render real-time metrics"""
        with ui.card().classes('w-full p-6'):
            ui.label('Live Metrics').classes('text-lg font-semibold mb-4')
            
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('flex-1 bg-blue-50'):
                    with ui.column().classes('p-4 items-center'):
                        ui.label('Pages (Done/Found/Limit)').classes('text-sm text-gray-600 mb-2')
                        self.pages_metric = ui.label('0/0').classes('text-3xl font-bold')
                
                with ui.card().classes('flex-1 bg-red-50'):
                    with ui.column().classes('p-4 items-center'):
                        ui.label('Errors').classes('text-sm text-gray-600 mb-2')
                        self.errors_metric = ui.label('0').classes('text-3xl font-bold text-red-600')
                
                with ui.card().classes('flex-1 bg-green-50'):
                    with ui.column().classes('p-4 items-center'):
                        ui.label('Speed').classes('text-sm text-gray-600 mb-2')
                        self.speed_metric = ui.label('0 p/s').classes('text-3xl font-bold')
                
                with ui.card().classes('flex-1 bg-yellow-50'):
                    with ui.column().classes('p-4 items-center'):
                        ui.label('ETA').classes('text-sm text-gray-600 mb-2')
                        self.eta_metric = ui.label('--').classes('text-3xl font-bold')
    
    def _render_activity_log(self):
        """Render activity log"""
        with ui.card().classes('w-full p-6'):
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('Activity Log').classes('text-lg font-semibold')
                self.auto_scroll_checkbox = ui.checkbox('Auto-scroll', value=True)
                self.auto_scroll_checkbox.on_value_change(self._on_auto_scroll_toggle)
            
            self.log_container = ui.log().classes('w-full h-64')
    
    def _render_preview(self):
        """Render page preview section"""
        with ui.card().classes('w-full p-6'):
            ui.label('📖 Preview').classes('text-lg font-semibold mb-4')
            self.preview_label = ui.label('First page preview will appear here...').classes('text-gray-600')
    
    def _on_auto_scroll_toggle(self, e):
        """Handle auto-scroll toggle - reliable callback"""
        self.auto_scroll_enabled = e.value
    
    async def _start_monitoring(self):
        """Start monitoring the crawl progress from real state manager"""
        while self.is_running:
            # Get current state from state manager
            state = self.state_manager.get_state(self.crawl_id)
            
            if not state:
                ui.notify('Crawl not found', type='negative')
                await asyncio.sleep(1)
                ui.navigate.to('/')
                break
            
            # Update progress bar - use found pages (total_pages) as base, not limit
            if state.total_pages > 0:
                # Progress based on found pages: done / found
                progress = min(state.pages_crawled / state.total_pages, 1.0)  # Cap at 100%
            else:
                progress = 0
            
            self.progress_bar.value = progress
            
            # Update status text - show URL or page number
            if state.status == 'completed':
                self.status_text.text = '✅ Crawl complete!'
            elif state.status == 'error':
                self.status_text.text = '❌ Crawl failed!'
            elif state.current_url:
                self.status_text.text = f'📄 Crawling: {state.current_url}'
            else:
                self.status_text.text = f'📄 Processing page {state.current_page}/{state.total_pages if state.total_pages > 0 else "?"}...'
            
            # Update metrics - show done/found/limit format
            # pages_crawled = done, total_pages = found, max_pages = limit
            max_pages_config = state.config.get('max_pages', 0)
            
            # Format: done/found/limit
            if max_pages_config and max_pages_config > 0:
                self.pages_metric.text = f'{state.pages_crawled}/{state.total_pages}/{max_pages_config}'
            elif state.total_pages > 0:
                self.pages_metric.text = f'{state.pages_crawled}/{state.total_pages}'
            else:
                self.pages_metric.text = f'{state.pages_crawled}/...'
            self.errors_metric.text = str(state.errors)
            self.speed_metric.text = f'{state.speed:.1f} p/s'
            
            # Update ETA
            eta_seconds = state.get_eta()
            eta_mins = int(eta_seconds / 60)
            eta_secs = int(eta_seconds % 60)
            self.eta_metric.text = f'{eta_mins}m {eta_secs}s' if eta_seconds > 0 else '0m 0s'
            
            # Update log (incremental) - respect auto-scroll setting
            if len(state.log_entries) > self.last_log_count:
                new_entries = state.log_entries[self.last_log_count:]
                for entry in new_entries:
                    self.log_container.push(entry)
                
                self.last_log_count = len(state.log_entries)
                
                # Scroll to bottom if auto-scroll is enabled
                if self.auto_scroll_enabled:
                    # Force scroll after DOM update - use NiceGUI's built-in method
                    self.log_container.run_method('scrollToBottom')
                
                # Update preview with latest meaningful entry
                for entry in reversed(new_entries):
                    if 'Fetching' in entry or 'Crawling' in entry:
                        preview_text = entry.split(' - ')[-1] if ' - ' in entry else entry
                        self.preview_label.text = f'📄 {preview_text[:150]}...'
                        break
            
            # Check if completed - DON'T auto-redirect, let user review
            if state.status == 'completed':
                self.is_running = False
                ui.notify('✅ Crawl completed! View results below or click "DASHBOARD" to return.', type='positive', position='bottom-right', timeout=8, close_button=True)
                self.status_text.text = '✅ Crawl complete! Click button below to view results.'
                
                # Show results button
                with self.results_button_container:
                    ui.button(
                        '📊 View Results',
                        icon='visibility',
                        on_click=lambda: ui.navigate.to(f'/crawl/results/{self.crawl_id}')
                    ).props('size=lg color=primary unelevated')
                self.results_button_container.visible = True
                break
            
            elif state.status == 'error':
                self.is_running = False
                ui.notify('Crawl failed! Check logs for details.', type='negative')
                await asyncio.sleep(3)
                ui.navigate.to('/')
                break
            
            elif state.status == 'stopped':
                self.is_running = False
                ui.notify('Crawl stopped by user', type='warning')
                await asyncio.sleep(2)
                ui.navigate.to('/')
                break
            
            # Update every 500ms
            await asyncio.sleep(0.5)
    
    def _stop_crawl(self):
        """Stop the crawl"""
        with ui.dialog() as dialog, ui.card():
            ui.label('Stop Crawl?').classes('text-lg font-bold mb-4')
            ui.label('Are you sure? Progress will be saved but document may be incomplete.')\
                .classes('text-gray-600 mb-4')
            
            with ui.row().classes('gap-2'):
                ui.button('Cancel', on_click=dialog.close).props('outline')
                ui.button(
                    'Stop Crawl',
                    on_click=lambda: self._confirm_stop(dialog)
                ).props('color=negative')
        
        dialog.open()
    
    def _confirm_stop(self, dialog):
        """Confirm stop action"""
        self.is_running = False
        dialog.close()
        ui.notify('Crawl stopped', type='warning')
        
        # Navigate back to dashboard
        ui.timer(1, lambda: ui.navigate.to('/'), once=True)
