import logging
import hashlib
import requests
from pathlib import Path
from urllib.parse import urljoin
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


class ImageHandler:
    def __init__(self, cache_dir: str = "cache/images"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.failed_images = set()
    
    def download_image(self, img_url: str, base_url: str, max_width: int = 800, max_height: int = 600) -> Path:
        """
        Download and cache image, optimizing size.
        
        Args:
            img_url: Image URL (relative or absolute)
            base_url: Base URL for relative URLs
            max_width: Max width for image
            max_height: Max height for image
            
        Returns:
            Path to cached image file, or None if failed
        """
        try:
            absolute_url = urljoin(base_url, img_url)
            
            filename_hash = hashlib.md5(absolute_url.encode()).hexdigest()
            
            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                cache_path = self.cache_dir / f"{filename_hash}{ext}"
                if cache_path.exists():
                    logger.debug(f"Image cache hit: {cache_path}")
                    return cache_path
            
            logger.info(f"Downloading image: {absolute_url}")
            response = requests.get(absolute_url, timeout=10)
            response.raise_for_status()
            
            if Image is None:
                logger.warning("PIL not available, skipping image optimization")
                cache_path = self.cache_dir / f"{filename_hash}.png"
                cache_path.write_bytes(response.content)
                return cache_path
            
            img = Image.open(BytesIO(response.content))
            
            if img.mode == 'RGBA' or img.format == 'PNG':
                ext = '.png'
            else:
                ext = '.jpg'
                if img.mode != 'RGB':
                    img = img.convert('RGB')
            
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            cache_path = self.cache_dir / f"{filename_hash}{ext}"
            if ext == '.png':
                img.save(cache_path, 'PNG', optimize=True)
            else:
                img.save(cache_path, 'JPEG', quality=85, optimize=True)
            
            logger.info(f"Cached image: {cache_path} ({img.size})")
            return cache_path
        
        except Exception as e:
            logger.error(f"Failed to download image {img_url}: {e}")
            self.failed_images.add(img_url)
            return None
