import time
import logging
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Respect robots.txt and implement request throttling."""
    
    def __init__(self, user_agent: str = "Mozilla/5.0"):
        self.user_agent = user_agent
        self.robot_parsers: Dict[str, RobotFileParser] = {}
        self.last_request_time: Dict[str, float] = {}
        self.min_delay = 1.0
    
    def _get_robots_parser(self, url: str) -> Optional[RobotFileParser]:
        """Get or create robots.txt parser for domain."""
        domain = urlparse(url).netloc
        
        if domain in self.robot_parsers:
            return self.robot_parsers[domain]
        
        try:
            rp = RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            logger.debug(f"Fetching robots.txt from: {robots_url}")
            rp.set_url(robots_url)
            rp.read()
            self.robot_parsers[domain] = rp
            return rp
        except Exception as e:
            logger.warning(f"Could not parse robots.txt for {domain}: {e}")
            self.robot_parsers[domain] = None
            return None
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        rp = self._get_robots_parser(url)
        if rp is None:
            return True
        
        can_fetch = rp.can_fetch(self.user_agent, url)
        if not can_fetch:
            logger.warning(f"Blocked by robots.txt: {url}")
        
        return can_fetch
    
    def get_crawl_delay(self, url: str) -> float:
        """Get crawl delay for domain from robots.txt."""
        rp = self._get_robots_parser(url)
        if rp is None:
            return self.min_delay
        
        delay = rp.crawl_delay(self.user_agent)
        if delay is None:
            delay = rp.request_rate(self.user_agent)
            if delay is not None:
                delay = 1.0 / delay.requests
        
        return delay or self.min_delay
    
    def wait_if_needed(self, url: str):
        """Wait before fetching if necessary to respect rate limits."""
        domain = urlparse(url).netloc
        
        if domain not in self.last_request_time:
            self.last_request_time[domain] = time.time()
            return
        
        delay = self.get_crawl_delay(url)
        time_since_last = time.time() - self.last_request_time[domain]
        
        if time_since_last < delay:
            wait_time = delay - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
            time.sleep(wait_time)
        
        self.last_request_time[domain] = time.time()
