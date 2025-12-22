"""
Analytics service for dashboard statistics
"""

from datetime import datetime, timedelta
import random


class AnalyticsService:
    """Provides analytics data for the dashboard"""
    
    def __init__(self):
        self.data = self._generate_mock_data()
    
    def get_stats(self):
        """Get overview statistics"""
        from services.crawl_state_manager import CrawlStateManager
        state_manager = CrawlStateManager()
        recent = state_manager.get_recent_crawls(1000)
        
        if not recent:
            return {
                'total_crawls': 0,
                'success_rate': 0,
                'avg_time': 0,
                'total_pages': 0
            }
        
        completed = [c for c in recent if c.status == 'completed']
        success_rate = round((len(completed) / len(recent)) * 100, 1) if recent else 0
        avg_time = round(sum(c.get_duration() for c in completed) / len(completed), 1) if completed else 0
        total_pages = sum(c.pages_crawled for c in recent)
        
        return {
            'total_crawls': len(recent),
            'success_rate': success_rate,
            'avg_time': avg_time,
            'total_pages': total_pages
        }
    
    def get_activity_chart_data(self, days=30):
        """Get activity data for the last N days"""
        dates = []
        crawls = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i-1)
            dates.append(date.strftime('%m-%d'))
            crawls.append(random.randint(0, 10))
        
        return {
            'dates': dates,
            'crawls': crawls
        }
    
    def _generate_mock_data(self):
        """Generate mock data for development"""
        return {
            'daily_crawls': [3, 5, 2, 8, 4, 6, 7, 3, 9, 4],
            'popular_sites': ['pCloud API', 'GitHub Docs', 'Stripe API']
        }
