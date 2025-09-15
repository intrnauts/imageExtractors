from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import re

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
