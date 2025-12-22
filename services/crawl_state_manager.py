"""
Crawl State Manager - Manages active crawl states and results
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class CrawlState:
    """State of a running or completed crawl"""
    crawl_id: str
    config: dict
    status: str = 'initializing'  # initializing, running, completed, error, stopped
    
    # Progress
    current_page: int = 0
    total_pages: int = 0
    current_url: str = ''
    
    # Metrics
    pages_crawled: int = 0
    errors: int = 0
    warnings: int = 0
    speed: float = 0.0  # pages per second
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Results
    crawled_pages: Dict = field(default_factory=dict)
    output_path: str = ''
    html_path: str = ''
    log_path: str = ''
    
    # Logs
    log_entries: List[str] = field(default_factory=list)
    
    def add_log(self, message: str):
        """Add a log entry"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_entries.append(f"{timestamp} {message}")
    
    def save_metadata(self, output_dir: str):
        """Save crawl metadata to JSON file for persistence"""
        import json
        from pathlib import Path
        
        metadata = {
            'crawl_id': self.crawl_id,
            'url': self.config.get('url', ''),
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'pages_crawled': self.pages_crawled,
            'total_pages': self.total_pages,
            'current_page': self.current_page,
            'errors': self.errors,
            'warnings': self.warnings,
            'speed': self.speed,
            'duration': self.get_duration(),
            'output_path': self.output_path,
            'html_path': self.html_path,
            'log_path': self.log_path,
            'nav_strategy': self.config.get('nav_strategy', ''),
            'template_id': self.config.get('template_id', '')
        }
        
        metadata_file = Path(output_dir) / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def get_eta(self) -> int:
        """Calculate ETA in seconds"""
        if self.speed > 0 and self.total_pages > 0:
            remaining = self.total_pages - self.current_page
            return int(remaining / self.speed)
        return 0
    
    def get_duration(self) -> float:
        """Get crawl duration in seconds"""
        if self.start_time:
            end = self.end_time or datetime.now()
            return (end - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'crawl_id': self.crawl_id,
            'status': self.status,
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'current_url': self.current_url,
            'pages_crawled': self.pages_crawled,
            'errors': self.errors,
            'warnings': self.warnings,
            'speed': self.speed,
            'eta': self.get_eta(),
            'duration': self.get_duration(),
            'log_entries': self.log_entries[-50:],
            'output_path': self.output_path,
            'html_path': self.html_path,
            'log_path': self.log_path
        }


class CrawlStateManager:
    """Singleton manager for all crawl states"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.states: Dict[str, CrawlState] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        # Load persisted states
        self._load_persisted_states()
    
    def _load_persisted_states(self):
        """Load crawl states from output directory - supports both new folder structure and old flat files"""
        from pathlib import Path
        import yaml
        import re
        
        output_dir = Path(__file__).parent.parent / 'output'
        if not output_dir.exists():
            return
        
        # NEW STRUCTURE: Load from folders with timestamp pattern (any prefix)
        # Matches: pcloud_api_2024-12-19_14-30-15/, github_repo_2024-12-19_14-30-15/, crawl_2024-12-19_14-30-15/
        timestamp_pattern = re.compile(r'.*_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}.*')
        
        for crawl_folder in output_dir.iterdir():
            if not crawl_folder.is_dir():
                continue
            
            # Check if folder name matches timestamp pattern
            if not timestamp_pattern.match(crawl_folder.name):
                continue
            
            config_file = crawl_folder / 'config.yaml'
            if not config_file.exists():
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                crawl_id = config.get('crawl_id', crawl_folder.name.replace('crawl_', ''))
                
                # PRIORITY: Load from metadata.json if exists (most reliable)
                metadata_file = crawl_folder / 'metadata.json'
                if metadata_file.exists():
                    import json
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    state = CrawlState(
                        crawl_id=metadata['crawl_id'],
                        config=config,
                        status=metadata.get('status', 'completed'),
                        start_time=datetime.fromisoformat(metadata['start_time']) if metadata.get('start_time') else datetime.fromtimestamp(config_file.stat().st_mtime),
                        end_time=datetime.fromisoformat(metadata['end_time']) if metadata.get('end_time') else datetime.fromtimestamp(config_file.stat().st_mtime),
                        pages_crawled=metadata.get('pages_crawled', 0),
                        total_pages=metadata.get('total_pages', 0),
                        current_page=metadata.get('current_page', 0),
                        errors=metadata.get('errors', 0),
                        warnings=metadata.get('warnings', 0),
                        speed=metadata.get('speed', 0.0),
                        output_path=metadata.get('output_path', ''),
                        html_path=metadata.get('html_path', ''),
                        log_path=metadata.get('log_path', '')
                    )
                else:
                    # FALLBACK: Create state from config and try to parse logs
                    state = CrawlState(
                        crawl_id=crawl_id,
                        config=config,
                        status='completed',
                        start_time=datetime.fromisoformat(config.get('timestamp')) if config.get('timestamp') else datetime.fromtimestamp(config_file.stat().st_mtime),
                        end_time=datetime.fromtimestamp(config_file.stat().st_mtime)
                    )
                
                # If no metadata.json, try to get pages_crawled from log file (fallback)
                log_files = list(crawl_folder.glob('*.log'))
                if log_files:
                    log_file = log_files[0]
                    state.log_path = str(log_file)
                    with open(log_file, 'r', encoding='utf-8') as lf:
                        for line in lf:
                            if 'Crawled' in line and 'pages' in line:
                                match = re.search(r'Crawled (\d+) pages', line)
                                if match:
                                    state.pages_crawled = int(match.group(1))
                                    break
                
                # Find output files
                docx_files = list(crawl_folder.glob('*.docx'))
                if docx_files and not docx_files[0].name.startswith('~'):
                    state.output_path = str(docx_files[0])
                
                html_files = list(crawl_folder.glob('index.html'))
                if html_files:
                    state.html_path = str(html_files[0])
                
                self.states[crawl_id] = state
                logger.debug(f"Loaded crawl state from folder: {crawl_folder.name}")
                
            except Exception as e:
                logger.warning(f"Failed to load state from {crawl_folder}: {e}")
        
        # OLD STRUCTURE: Load from flat config_*.yaml files (backwards compatibility)
        for config_file in output_dir.glob('config_*.yaml'):
            try:
                crawl_id = config_file.stem.replace('config_', '')
                
                # Skip if already loaded from new structure
                if crawl_id in self.states:
                    continue
                
                # Try to load metadata first
                metadata = None
                metadata_file = output_dir / f'metadata_{crawl_id}.yaml'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = yaml.safe_load(f)
                    except:
                        pass
                
                # Load base config
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # Build state config
                state_config = {
                    'url': metadata.get('url') if metadata else 'Unknown URL',
                    'output_name': metadata.get('output_name') if metadata else config.get('output_name', 'output'),
                    'nav_strategy': metadata.get('nav_strategy') if metadata else config.get('crawler', {}).get('nav_strategy', 'pcloud'),
                    'template_id': metadata.get('template_id') if metadata else 'custom'
                }
                
                # Create state
                state = CrawlState(
                    crawl_id=crawl_id,
                    config=state_config,
                    status='completed',
                    start_time=datetime.fromisoformat(metadata.get('timestamp')) if metadata and metadata.get('timestamp') else datetime.fromtimestamp(config_file.stat().st_mtime),
                    end_time=datetime.fromtimestamp(config_file.stat().st_mtime)
                )
                
                # Try to get pages_crawled from log file
                log_file = output_dir / f"{state_config.get('output_name', 'crawl')}.log"
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as lf:
                        for line in lf:
                            if 'Visited' in line and 'pages' in line:
                                match = re.search(r'Visited (\\d+) pages', line)
                                if match:
                                    state.pages_crawled = int(match.group(1))
                                    break
                
                # Find docx output
                output_name = state_config.get('output_name', 'output')
                for docx in output_dir.glob(f'{output_name}*.docx'):
                    if not docx.name.startswith('~'):  # Skip temp files
                        state.output_path = str(docx)
                        break
                
                self.states[crawl_id] = state
            except Exception:
                pass
    
    def create_crawl(self, crawl_id: str, config: dict) -> CrawlState:
        """Create a new crawl state"""
        with self._lock:
            state = CrawlState(
                crawl_id=crawl_id,
                config=config,
                start_time=datetime.now()
            )
            self.states[crawl_id] = state
            return state
    
    def get_state(self, crawl_id: str) -> Optional[CrawlState]:
        """Get crawl state by ID"""
        return self.states.get(crawl_id)
    
    def update_progress(self, crawl_id: str, **kwargs):
        """Update crawl progress"""
        state = self.get_state(crawl_id)
        if state:
            with self._lock:
                for key, value in kwargs.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
    
    def add_log(self, crawl_id: str, message: str):
        """Add a log entry"""
        state = self.get_state(crawl_id)
        if state:
            state.add_log(message)
    
    def complete_crawl(self, crawl_id: str, output_path: str):
        """Mark crawl as completed"""
        state = self.get_state(crawl_id)
        if state:
            with self._lock:
                state.status = 'completed'
                state.end_time = datetime.now()
                state.output_path = output_path
    
    def error_crawl(self, crawl_id: str, error: str):
        """Mark crawl as error"""
        state = self.get_state(crawl_id)
        if state:
            with self._lock:
                state.status = 'error'
                state.end_time = datetime.now()
                state.add_log(f"❌ Error: {error}")
    
    def stop_crawl(self, crawl_id: str):
        """Stop a running crawl"""
        state = self.get_state(crawl_id)
        if state:
            with self._lock:
                state.status = 'stopped'
                state.end_time = datetime.now()
    
    def get_all_states(self) -> List[CrawlState]:
        """Get all crawl states"""
        return list(self.states.values())
    
    def get_recent_crawls(self, limit: int = 10) -> List[CrawlState]:
        """Get recent crawls sorted by start time"""
        crawls = sorted(
            self.states.values(),
            key=lambda x: x.start_time or datetime.min,
            reverse=True
        )
        return crawls[:limit]
    
    def delete_crawl(self, crawl_id: str) -> bool:
        """Delete a single crawl and its folder"""
        from pathlib import Path
        import shutil
        
        state = self.get_state(crawl_id)
        if not state:
            return False
        
        try:
            # Find and delete the crawl folder
            output_dir = Path(__file__).parent.parent / 'output'
            
            # Look for folder containing this crawl's files
            for crawl_folder in output_dir.iterdir():
                if not crawl_folder.is_dir():
                    continue
                
                config_file = crawl_folder / 'config.yaml'
                if config_file.exists():
                    try:
                        import yaml
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                        
                        if config.get('crawl_id') == crawl_id:
                            # Found the folder, delete it
                            shutil.rmtree(crawl_folder)
                            logger.info(f"Deleted crawl folder: {crawl_folder}")
                            break
                    except:
                        pass
            
            # Remove from states
            with self._lock:
                if crawl_id in self.states:
                    del self.states[crawl_id]
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete crawl {crawl_id}: {e}")
            return False
    
    def delete_all_crawls(self) -> bool:
        """Delete all crawls and their folders"""
        from pathlib import Path
        import shutil
        import re
        
        try:
            output_dir = Path(__file__).parent.parent / 'output'
            if not output_dir.exists():
                return True
            
            timestamp_pattern = re.compile(r'.*_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}.*')
            
            # Delete all timestamp-based folders
            for crawl_folder in output_dir.iterdir():
                if not crawl_folder.is_dir():
                    continue
                
                if timestamp_pattern.match(crawl_folder.name):
                    try:
                        shutil.rmtree(crawl_folder)
                        logger.info(f"Deleted crawl folder: {crawl_folder}")
                    except Exception as e:
                        logger.error(f"Failed to delete folder {crawl_folder}: {e}")
            
            # Clear all states
            with self._lock:
                self.states.clear()
            
            logger.info("Deleted all crawls")
            return True
        except Exception as e:
            logger.error(f"Failed to delete all crawls: {e}")
            return False
