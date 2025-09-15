# client.py
import httpx
from typing import Dict, List, Optional

class ImageExtractorClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def extract_images(self, url: str, options: Optional[Dict] = None) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/extract",
                json={"url": url, "options": options or {}}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_supported_platforms(self) -> List[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/platforms")
            return response.json()["platforms"]

# Usage in your other apps:
client = ImageExtractorClient()
result = await client.extract_images("https://flickr.com/photos/user/123456")
