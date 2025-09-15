from typing import Optional, List
from .base import BaseExtractor

class ExtractorRegistry:
    def __init__(self):
        self.extractors = []
        self._register_extractors()
    
    def _register_extractors(self):
        """Register all available extractors"""
        from .flickr import FlickrExtractor
        # Comment out the ones you haven't created yet
        # from .imgur import ImgurExtractor
        # from .instagram import InstagramExtractor
        
        self.extractors.extend([
            FlickrExtractor(),
            # ImgurExtractor(),
            # InstagramExtractor(),
        ])
    
    def get_extractor(self, url: str) -> Optional[BaseExtractor]:
        """Find the appropriate extractor for a URL"""
        for extractor in self.extractors:
            if extractor.matches_url(url):
                return extractor
        return None
    
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platform names"""
        return [e.platform_name for e in self.extractors]
