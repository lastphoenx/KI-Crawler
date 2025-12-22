"""
Professional Web Crawler - NiceGUI Edition
Entry point for the web interface
"""

from nicegui import ui, app
from app.router import setup_routes
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def ensure_directories():
    """Create necessary directories if they don't exist"""
    directories = ['output', 'cache', 'logs', 'static', 'templates']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    logger.info("✓ All required directories exist")


# Ensure directories exist before starting
ensure_directories()

# Add static files
app.add_static_files('/static', 'static')

# Custom CSS for professional look (shared=True for all pages)
ui.add_head_html('''
<style>
    /* Custom Tailwind extensions */
    .glassmorphism {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    .hover-lift {
        transition: transform 0.2s ease-in-out;
    }
    
    .hover-lift:hover {
        transform: translateY(-4px);
    }
    
    .gradient-bg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Card hover effects */
    .stat-card {
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    
    /* Fix notifications - appear below header (header is at top with z-index) */
    .q-notifications {
        z-index: 9998 !important; /* Below header (z-index: 9999) */
        top: 70px !important; /* Below 64px header + margin */
    }
    
    .q-notification {
        margin-top: 8px;
    }
</style>
''', shared=True)

# Setup all routes
setup_routes()

# Run app
if __name__ in {'__main__', '__mp_main__'}:
    logger.info("Starting Web Crawler UI...")
    
    ui.run(
        title='Professional Web Crawler',
        port=8080,
        reload=False,     # Disabled to avoid multiple instances
        show=True,        # Open browser automatically
        favicon='🕷️'
    )
