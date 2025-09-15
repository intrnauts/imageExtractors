# extractors/__init__.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import re
from urllib.parse import urlparse

class BaseExtractor(ABC):
    """Base class for all image extractors"""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def url_patterns(self) -> List[str]:
        """Regex patterns to match URLs for this platform"""
        pass
    
    @abstractmethod
    async def extract(self, url: str, options: Dict) -> Dict:
        pass
    
    def matches_url(self, url: str) -> bool:
        """Check if this extractor can handle the given URL"""
        for pattern in self.url_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

class ExtractorRegistry:
    def __init__(self):
        self.extractors = []
        self._register_extractors()
    
    def _register_extractors(self):
        """Register all available extractors"""
        from .flickr import FlickrExtractor
        from .imgur import ImgurExtractor
        from .instagram import InstagramExtractor
        # Add more as needed
        
        self.extractors.extend([
            FlickrExtractor(),
            ImgurExtractor(),
            InstagramExtractor(),
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
