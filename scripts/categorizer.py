import logging
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class MethodCategorizer:
    def __init__(self):
        self.category_keywords = {
            'General': ['general', 'userinfo', 'getip', 'currentserver', 'getdigest', 'diff', 'feedback'],
            'Folder': ['folder', 'createfolder', 'listfolder', 'renamefolder', 'deletefolder', 'copyfolder'],
            'File': ['file', 'uploadfile', 'downloadfile', 'copyfile', 'deletefile', 'renamefile', 'stat', 'checksumfile'],
            'Auth': ['auth', 'sendverificationemail', 'verifyemail', 'changepassword', 'lostpassword', 'resetpassword', 'register', 'logout', 'deactivateuser'],
            'Streaming': ['streaming', 'getfilelink', 'getvideolink', 'getaudiolink', 'gethlslink', 'gettextfile'],
            'Archiving': ['archiving', 'getzip', 'savezip', 'extractarchive'],
            'Sharing': ['sharing', 'sharefolder', 'listshares', 'acceptshare', 'declineshare', 'removeshare'],
            'Public Links': ['public', 'publiclink', 'getpubliclink', 'deletepubliclink'],
            'Thumbnails': ['thumbnail', 'getthumb'],
            'Upload Links': ['upload', 'uploadlink'],
            'Revisions': ['revision', 'getfilehistory'],
            'Newsletter': ['newsletter'],
            'Trash': ['trash', 'deleteforever'],
            'Collection': ['collection'],
            'Transfer': ['transfer'],
            'OAuth': ['oauth'],
        }
    
    def categorize_methods(self, pages_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group methods by category"""
        categories = defaultdict(list)
        uncategorized = []
        
        for page in pages_data:
            if page.get('type') != 'api_method':
                continue
            
            category = self._find_category(page)
            if category:
                categories[category].append(page)
            else:
                uncategorized.append(page)
        
        if uncategorized:
            categories['Other'] = uncategorized
        
        return dict(categories)
    
    def _find_category(self, page: Dict[str, Any]) -> str:
        """Find category for a page"""
        name = (page.get('name') or '').lower()
        url = (page.get('url') or '').lower()
        
        search_text = f"{name} {url}"
        
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword.lower() in search_text:
                    return category
        
        if '/methods/' in url:
            parts = url.split('/methods/')
            if len(parts) > 1:
                category_part = parts[1].split('/')[0]
                return category_part.replace('_', ' ').title()
        
        return None
    
    def sort_categories(self, categories: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Sort categories in logical order"""
        order = [
            'General', 'Folder', 'File', 'Auth', 'Streaming', 
            'Archiving', 'Sharing', 'Public Links', 'Thumbnails',
            'Upload Links', 'Revisions', 'Newsletter', 'Trash',
            'Collection', 'Transfer', 'OAuth', 'Other'
        ]
        
        sorted_cats = {}
        for cat in order:
            if cat in categories:
                sorted_cats[cat] = categories[cat]
        
        for cat in categories:
            if cat not in sorted_cats:
                sorted_cats[cat] = categories[cat]
        
        return sorted_cats
