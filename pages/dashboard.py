"""
Dashboard page - Main landing page with overview
"""

from nicegui import ui
from services.analytics_service import AnalyticsService
from services.crawler_service import CrawlerService


class DashboardPage:
    """Dashboard page with statistics and quick actions"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        self.crawler_service = CrawlerService()
        self.selected_crawl_id = None  # Track selected crawl
    
    def render(self):
        """Render the dashboard page"""
        with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-8'):
            # Welcome Header
            self._render_welcome()
            
            # Quick Stats
            self._render_stats()
            
            # Quick Actions
            self._render_quick_actions()
            
            # Activity Chart
            self._render_activity_chart()
            
            # Recent Crawls
            self._render_recent_crawls()
    
    def _render_welcome(self):
        """Render welcome section"""
        ui.label('Welcome back! 👋').classes('text-3xl font-bold text-gray-800')
        ui.label('Here\'s what\'s happening with your crawls').classes('text-gray-600 mb-4')
    
    def _render_stats(self):
        """Render statistics cards"""
        ui.label('Quick Stats').classes('text-xl font-semibold mb-4')
        
        stats = self.analytics.get_stats()
        
        with ui.row().classes('w-full gap-4 mb-6'):
            self._stat_card(
                '📊', 
                'Total Crawls', 
                str(stats['total_crawls']),
                'indigo'
            )
            
            self._stat_card(
                '✅', 
                'Success Rate', 
                f"{stats['success_rate']}%",
                'green'
            )
            
            self._stat_card(
                '⚡', 
                'Avg Time', 
                f"{stats['avg_time']}s",
                'yellow'
            )
            
            self._stat_card(
                '📄', 
                'Pages Crawled', 
                f"{stats['total_pages']:,}",
                'blue'
            )
    
    def _stat_card(self, icon, label, value, color):
        """Render a single statistics card"""
        with ui.card().classes(f'flex-1 bg-{color}-50 border-l-4 border-{color}-500 stat-card hover-lift'):
            with ui.column().classes('p-6 gap-2'):
                ui.label(icon).classes('text-4xl')
                ui.label(str(value)).classes('text-3xl font-bold text-gray-800')
                ui.label(label).classes('text-sm text-gray-600')
    
    def _render_quick_actions(self):
        """Render quick action buttons"""
        ui.label('Quick Actions').classes('text-xl font-semibold mb-4')
        
        with ui.row().classes('gap-4 mb-6'):
            ui.button('+ New Crawl', on_click=lambda: ui.navigate.to('/crawl/new'))\
                .props('icon=add color=primary size=lg unelevated')
            
            ui.button('📋 Templates', on_click=lambda: ui.navigate.to('/templates'))\
                .props('outline color=secondary size=lg')
            
            ui.button('📁 View History', on_click=lambda: ui.navigate.to('/history'))\
                .props('outline color=secondary size=lg')
    
    def _render_activity_chart(self):
        """Render activity chart"""
        ui.label('Activity (Last 30 Days)').classes('text-xl font-semibold mb-4')
        
        chart_data = self.analytics.get_activity_chart_data()
        
        with ui.card().classes('w-full mb-6'):
            # Using ECharts for nice visualization
            chart_options = {
                'xAxis': {
                    'type': 'category',
                    'data': chart_data['dates']
                },
                'yAxis': {
                    'type': 'value',
                    'name': 'Crawls'
                },
                'series': [{
                    'data': chart_data['crawls'],
                    'type': 'line',
                    'smooth': True,
                    'areaStyle': {
                        'color': 'rgba(102, 126, 234, 0.3)'
                    },
                    'lineStyle': {
                        'color': '#667eea',
                        'width': 3
                    },
                    'itemStyle': {
                        'color': '#667eea'
                    }
                }],
                'tooltip': {
                    'trigger': 'axis'
                },
                'grid': {
                    'left': '3%',
                    'right': '4%',
                    'bottom': '3%',
                    'containLabel': True
                }
            }
            
            ui.echart(chart_options).classes('h-64')
    
    def _render_recent_crawls(self):
        """Render recent crawls list"""
        ui.label('Recent Crawls').classes('text-xl font-semibold mb-4')
        
        # Get real crawl data from state manager
        crawls_list = self.crawler_service.get_recent_crawls(limit=5)
        
        if not crawls_list:
            ui.label('📭 No crawls yet. Start your first crawl!').classes('text-gray-500 text-lg')
            return
        
        with ui.card().classes('w-full'):
            for i, crawl in enumerate(crawls_list):
                self._crawl_row(crawl, is_last=(i == len(crawls_list) - 1))
    
    def _crawl_row(self, crawl, is_last=False):
        """Render a single crawl row"""
        border_class = '' if is_last else 'border-b border-gray-200'
        crawl_id = crawl['id']
        
        # Dynamic classes based on selection
        bg_class = 'bg-blue-100' if self.selected_crawl_id == crawl_id else 'hover:bg-gray-50'
        
        def toggle_selection():
            """Toggle selection state"""
            if self.selected_crawl_id == crawl_id:
                self.selected_crawl_id = None  # Deselect
            else:
                self.selected_crawl_id = crawl_id  # Select
            # Re-render to update UI (NiceGUI will handle this)
        
        with ui.row().classes(f'w-full items-center p-4 cursor-pointer transition-colors {border_class} {bg_class}') \
                .on('click', toggle_selection):
            # Status Icon
            status_icon = '✅' if crawl['status'] == 'success' else '⚠️'
            ui.label(status_icon).classes('text-2xl')
            
            # Crawl Info
            with ui.column().classes('flex-1 ml-4 gap-1'):
                ui.label(crawl['url']).classes('font-semibold text-gray-800')
                ui.label(
                    f"{crawl['pages']} pages • {crawl['duration']:.1f}s • {crawl['time_ago']}"
                ).classes('text-sm text-gray-600')
            
            # Actions
            with ui.row().classes('gap-2'):
                ui.button(
                    icon='download',
                    on_click=lambda c=crawl: self._download_crawl(c['id'])
                ).props('flat dense round').tooltip('Download')
                
                ui.button(
                    icon='refresh',
                    on_click=lambda c=crawl: self._rerun_crawl(c['id'])
                ).props('flat dense round').tooltip('Re-run')
                
                ui.button(
                    icon='info',
                    on_click=lambda c=crawl: self._show_details(c['id'])
                ).props('flat dense round').tooltip('Details')
                
                ui.button(
                    icon='delete',
                    on_click=lambda c=crawl: self._delete_crawl(c['id'], c['url'])
                ).props('flat dense round').classes('text-red-600').tooltip('Delete')
    
    def _download_crawl(self, crawl_id):
        """Handle download action"""
        state = self.crawler_service.state_manager.get_state(crawl_id)
        if state and state.output_path:
            from pathlib import Path
            output_file = Path(state.output_path)
            if output_file.exists():
                import shutil
                import os
                downloads_dir = Path(os.path.expanduser('~')) / 'Downloads'
                downloads_dir.mkdir(exist_ok=True)
                dest = downloads_dir / output_file.name
                shutil.copy2(output_file, dest)
                ui.notify(f'✅ Copied to Downloads: {output_file.name}', type='positive')
            else:
                ui.notify('File not found', type='negative')
        else:
            ui.notify('No output file available', type='warning')
    
    def _rerun_crawl(self, crawl_id):
        """Handle re-run action"""
        state = self.crawler_service.state_manager.get_state(crawl_id)
        if state:
            # Navigate to new crawl with same URL
            ui.navigate.to(f'/crawl/new?url={state.config.get("url", "")}')
            ui.notify('Starting new crawl...', type='info')
        else:
            ui.notify('Crawl not found', type='negative')
    
    def _show_details(self, crawl_id):
        """Show crawl details"""
        ui.navigate.to(f'/crawl/results/{crawl_id}')
    
    def _delete_crawl(self, crawl_id: str, url: str):
        """Confirm and delete a crawl"""
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
            with ui.column().classes('gap-4 p-6'):
                ui.label('Delete Crawl?').classes('text-xl font-bold')
                ui.label(f'URL: {url}').classes('text-sm text-gray-600')
                ui.label('This action cannot be undone.').classes('text-sm text-red-600 font-semibold')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).props('outline')
                    ui.button('Delete', on_click=lambda: [self._confirm_delete(crawl_id), dialog.close()]).classes('bg-red-600 text-white')
        
        dialog.open()
    
    def _confirm_delete(self, crawl_id: str):
        """Execute crawl deletion"""
        if self.crawler_service.state_manager.delete_crawl(crawl_id):
            ui.notify('✅ Crawl deleted', type='positive')
            # Reload page to refresh the list
            import time
            time.sleep(0.5)
            ui.navigate.reload()
        else:
            ui.notify('❌ Failed to delete crawl', type='negative')
