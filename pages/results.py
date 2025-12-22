"""
Results Page - Display crawl results and download options
"""

from nicegui import ui
from services.crawl_state_manager import CrawlStateManager
import os


class ResultsPage:
    """Display crawl results with download options"""
    
    def __init__(self, crawl_id: str):
        self.crawl_id = crawl_id
        self.state_manager = CrawlStateManager()
        self.state = self.state_manager.get_state(crawl_id)
    
    def render(self):
        """Render the results page"""
        # Check if state exists
        if not self.state:
            with ui.column().classes('w-full max-w-7xl mx-auto p-6'):
                ui.label('❌ Crawl not found').classes('text-2xl font-bold text-red-600')
                ui.button('← Back to Dashboard', on_click=lambda: ui.navigate.to('/'))\
                    .props('outline')
            return
        
        with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-8'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-4'):
                status_emoji = '✅' if self.state.status == 'completed' else '⚠️'
                status_text = 'Complete!' if self.state.status == 'completed' else 'Finished with issues'
                ui.label(f'{status_emoji} Crawl {status_text}').classes('text-3xl font-bold text-green-600')
                ui.button(
                    '← Dashboard',
                    icon='home',
                    on_click=lambda: ui.navigate.to('/')
                ).props('outline')
            
            # Success Summary
            self._render_summary()
            
            # Download Section
            self._render_downloads()
            
            # Preview Section
            self._render_preview()
            
            # Statistics
            self._render_statistics()
            
            # Actions
            self._render_actions()
    
    def _render_summary(self):
        """Render success summary with real data"""
        if not self.state:
            return
        
        # Use pages_crawled, but fallback to actual data if it's 0
        actual_pages = self.state.pages_crawled
        if actual_pages == 0:
            # Fallback: use length of crawled_pages dict or current_page
            if hasattr(self.state, 'crawled_pages') and self.state.crawled_pages:
                actual_pages = len(self.state.crawled_pages)
            elif self.state.current_page > 0:
                actual_pages = self.state.current_page
        
        duration = (self.state.end_time - self.state.start_time).total_seconds() if self.state.end_time else 0
        success_color = 'green' if self.state.status == 'completed' else 'orange'
        speed = actual_pages / duration if duration > 0 else 0
        
        with ui.card().classes(f'w-full p-6 bg-{success_color}-50 border-l-4 border-{success_color}-500'):
            ui.label(f'🎉 Successfully crawled {actual_pages} pages in {duration:.1f}s').classes('text-xl font-semibold mb-2')
            with ui.column().classes('gap-1'):
                ui.label(f'• 📄 {actual_pages} pages processed').classes('text-gray-700')
                ui.label(f'• ⚡ Average speed: {speed:.2f} pages/sec').classes('text-gray-700')
                ui.label(f'• 🎯 Target URL: {self.state.config.get("url", "Unknown")}').classes('text-gray-700')
                if self.state.errors > 0:
                    ui.label(f'• ⚠️ {self.state.errors} errors encountered').classes('text-red-700')
                else:
                    ui.label('• ✅ No errors').classes('text-green-700')
    
    def _render_downloads(self):
        """Render download buttons with real file info"""
        if not self.state or not self.state.output_path:
            ui.label('📥 No output files available').classes('text-xl text-gray-500 mb-4')
            return
        
        ui.label('📥 Download Results').classes('text-2xl font-semibold mb-4')
        
        # Check for output files
        docx_path = self.state.output_path
        pdf_path = docx_path.replace('.docx', '.pdf') if docx_path else None
        
        with ui.row().classes('gap-4'):
            # DOCX Download
            if os.path.exists(docx_path):
                size_mb = os.path.getsize(docx_path) / (1024 * 1024)
                size_kb = os.path.getsize(docx_path) / 1024
                size_text = f'{size_mb:.2f} MB' if size_mb >= 1 else f'{size_kb:.1f} KB'
                
                with ui.card().classes('flex-1 hover-lift cursor-pointer'):
                    with ui.column().classes('p-6 items-center gap-3'):
                        ui.label('📄').classes('text-5xl')
                        ui.label('DOCX').classes('text-xl font-bold')
                        ui.label(size_text).classes('text-sm text-gray-600')
                        ui.label(os.path.basename(docx_path)).classes('text-xs text-gray-500 text-center')
                        ui.button('Download', icon='download')\
                            .props('color=primary').on('click', lambda: self._download_file(docx_path))
            
            # PDF Download (placeholder)
            with ui.card().classes('flex-1 hover-lift cursor-pointer'):
                with ui.column().classes('p-6 items-center gap-3'):
                    ui.label('📕').classes('text-5xl')
                    ui.label('PDF').classes('text-xl font-bold')
                    if pdf_path and os.path.exists(pdf_path):
                        size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                        ui.label(f'{size_mb:.2f} MB').classes('text-sm text-gray-600')
                        ui.button('Download', icon='download')\
                            .props('color=primary').on('click', lambda: self._download_file(pdf_path))
                    else:
                        ui.label('Generate from DOCX').classes('text-sm text-gray-500')
                        ui.button('Convert & Download', icon='picture_as_pdf')\
                            .props('color=primary').on('click', lambda: self._convert_to_pdf())
            
            # JSON Download (state export)
            with ui.card().classes('flex-1 hover-lift cursor-pointer'):
                with ui.column().classes('p-6 items-center gap-3'):
                    ui.label('📊').classes('text-5xl')
                    ui.label('JSON').classes('text-xl font-bold')
                    ui.label('Crawl Data').classes('text-sm text-gray-600')
                    ui.button('Download', icon='download')\
                        .props('color=primary').on('click', lambda: self._download_json())
        
        # Log File Section (if available)
        if hasattr(self.state, 'log_path') and self.state.log_path:
            from pathlib import Path
            log_path = Path(self.state.log_path)
            if log_path.exists():
                log_size_kb = log_path.stat().st_size / 1024
                ui.label('📋 Crawl Log').classes('text-xl font-semibold mt-6 mb-2')
                with ui.card().classes('w-full bg-blue-50 border-l-4 border-blue-500'):
                    with ui.row().classes('p-4 items-center justify-between'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('description', size='lg').classes('text-blue-600')
                            with ui.column().classes('gap-0'):
                                ui.label(log_path.name).classes('font-semibold')
                                ui.label(f'{log_size_kb:.1f} KB • Full crawl log with timestamps').classes('text-sm text-gray-600')
                        with ui.row().classes('gap-2'):
                            ui.button('VIEW', icon='visibility', on_click=lambda: self._view_log(self.state.log_path))\
                                .props('flat color=blue')
                            ui.button('DOWNLOAD', icon='download', on_click=lambda: self._download_file(str(log_path)))\
                                .props('unelevated color=blue')
    
    def _render_preview(self):
        """Render document preview"""
        ui.label('📖 Document Preview').classes('text-2xl font-semibold mb-4')
        
        with ui.card().classes('w-full p-6'):
            with ui.column().classes('gap-4'):
                ui.label('Table of Contents:').classes('font-semibold text-lg')
                
                toc_items = [
                    '1. Introduction',
                    '2. Authentication',
                    '   2.1 OAuth Flow',
                    '   2.2 API Keys',
                    '3. User Management',
                    '   3.1 Get User',
                    '   3.2 Update User',
                    '4. File Operations',
                    '   4.1 Upload File',
                    '   4.2 Download File',
                ]
                
                for item in toc_items:
                    ui.label(item).classes('text-gray-700 font-mono')
    
    def _render_statistics(self):
        """Render crawl statistics with real data"""
        if not self.state:
            return
        
        ui.label('📊 Statistics').classes('text-2xl font-semibold mb-4')
        
        with ui.card().classes('w-full p-6'):
            with ui.row().classes('w-full gap-8'):
                # Basic metrics
                with ui.column().classes('flex-1'):
                    ui.label('Overview').classes('font-semibold mb-3')
                    
                    duration = (self.state.end_time - self.state.start_time).total_seconds() if self.state.end_time else 0
                    
                    stats = [
                        ('Pages Crawled', str(self.state.current_page)),
                        ('Total Errors', str(self.state.errors)),
                        ('Avg Speed', f'{self.state.speed:.1f} p/s'),
                        ('Total Duration', f'{duration:.1f}s'),
                        ('Start Time', self.state.start_time.strftime('%H:%M:%S')),
                        ('End Time', self.state.end_time.strftime('%H:%M:%S') if self.state.end_time else 'N/A'),
                    ]
                    
                    for label, value in stats:
                        with ui.row().classes('justify-between mb-2'):
                            ui.label(label).classes('text-gray-700')
                            ui.label(value).classes('font-bold')
    
    def _render_actions(self):
        """Render action buttons"""
        ui.label('Actions').classes('text-2xl font-semibold mb-4')
        
        with ui.row().classes('gap-4'):
            ui.button(
                '🔄 Re-run Crawl',
                on_click=self._rerun_crawl
            ).props('outline color=secondary size=lg')
            
            ui.button(
                '📝 Edit Config',
                on_click=self._edit_config
            ).props('outline color=secondary size=lg')
            
            ui.button(
                '📧 Share',
                on_click=self._share_results
            ).props('outline color=secondary size=lg')
    
    def _download_file(self, file_path):
        """Copy file to Downloads folder and open in Explorer"""
        import shutil
        from pathlib import Path
        if os.path.exists(file_path):
            # Copy to Downloads
            downloads_dir = Path(os.path.expanduser('~')) / 'Downloads'
            downloads_dir.mkdir(exist_ok=True)
            dest = downloads_dir / Path(file_path).name
            shutil.copy2(file_path, dest)
            ui.notify(f'✅ Saved to Downloads: {Path(file_path).name}', type='positive', position='top')
            # Open Explorer at Downloads
            try:
                import subprocess
                subprocess.run(['explorer', '/select,', str(dest)])
            except:
                pass
        else:
            ui.notify('File not found!', type='negative')
    
    def _view_log(self, log_path):
        """Open log file in notepad"""
        if log_path and os.path.exists(log_path):
            import subprocess
            try:
                subprocess.Popen(['notepad', str(log_path)])
            except:
                ui.notify('Could not open log file', type='negative')
        else:
            ui.notify('Log file not found', type='negative')
    
    def _convert_to_pdf(self):
        """Convert DOCX to PDF using LibreOffice"""
        if not self.crawl_result.get('output_path'):
            ui.notify('No DOCX file found', type='negative')
            return
        
        import subprocess
        from pathlib import Path
        
        docx_path = Path(self.crawl_result['output_path'])
        if not docx_path.exists():
            ui.notify('DOCX file not found', type='negative')
            return
        
        pdf_path = docx_path.with_suffix('.pdf')
        
        ui.notify('🔄 Converting to PDF... This may take a moment.', type='info')
        
        try:
            # Try LibreOffice conversion (soffice must be in PATH or installed location)
            result = subprocess.run(
                ['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(docx_path.parent), str(docx_path)],
                capture_output=True,
                timeout=30,
                text=True
            )
            
            if result.returncode == 0 and pdf_path.exists():
                # Copy to Downloads
                import shutil
                downloads_dir = Path.home() / 'Downloads'
                dest = downloads_dir / pdf_path.name
                shutil.copy2(pdf_path, dest)
                
                # Open Explorer at Downloads
                subprocess.Popen(['explorer', '/select,', str(dest)])
                ui.notify(f'✅ PDF saved to Downloads: {pdf_path.name}', type='positive')
            else:
                ui.notify('⚠️ LibreOffice not found. Install LibreOffice for PDF export.', type='warning')
        except FileNotFoundError:
            ui.notify('⚠️ LibreOffice not installed. Download from: https://www.libreoffice.org', type='warning')
        except subprocess.TimeoutExpired:
            ui.notify('⏱️ PDF conversion timed out. File may be too large.', type='negative')
        except Exception as e:
            ui.notify(f'❌ PDF conversion failed: {str(e)}', type='negative')
    
    def _download_json(self):
        """Export crawl state as JSON"""
        import json
        from pathlib import Path
        
        if self.state:
            json_path = Path(self.state.output_path).with_suffix('.json')
            json_data = {
                'crawl_id': self.state.crawl_id,
                'url': self.state.config.get('url'),
                'pages_crawled': self.state.current_page,
                'errors': self.state.errors,
                'duration': self.state.get_duration(),
                'start_time': self.state.start_time.isoformat(),
                'end_time': self.state.end_time.isoformat() if self.state.end_time else None,
                'logs': self.state.log_entries
            }
            
            json_path.write_text(json.dumps(json_data, indent=2))
            ui.notify(f'JSON exported to: {json_path}', type='positive')
            
            try:
                import subprocess
                subprocess.run(['explorer', '/select,', str(json_path).replace('/', '\\')])
            except:
                pass
    
    def _rerun_crawl(self):
        """Re-run the crawl"""
        ui.notify('Re-running crawl with same configuration...', type='info')
        ui.navigate.to('/crawl/new')
    
    def _edit_config(self):
        """Edit configuration"""
        ui.navigate.to('/crawl/new')
    
    def _share_results(self):
        """Share results"""
        ui.notify('Share feature coming soon!', type='info')
