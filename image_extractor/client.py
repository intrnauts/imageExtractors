# client.py
import httpx
from typing import Dict, List, Optional

class ImageExtractorClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    async def extract_images(self, url: str, options: Optional[Dict] = None) -> Dict:
        """
        Extract images from the given URL.

        Args:
            url: The URL to extract images from
            options: Optional extraction options

        Returns:
            Dict containing extracted image information

        Raises:
            httpx.ConnectError: If unable to connect to the service
            httpx.TimeoutException: If the request times out
            httpx.HTTPStatusError: If the server returns an error status
            ValueError: If the response is not valid JSON
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/extract",
                    json={"url": url, "options": options or {}},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as e:
            raise httpx.ConnectError(f"Failed to connect to image extractor service at {self.base_url}: {e}")
        except httpx.TimeoutException as e:
            raise httpx.TimeoutException(f"Request timed out after {self.timeout}s: {e}")
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", "")
            except:
                error_detail = e.response.text
            raise httpx.HTTPStatusError(
                f"HTTP {e.response.status_code} error: {error_detail}",
                request=e.request,
                response=e.response
            )
    
    async def get_supported_platforms(self) -> List[str]:
        """
        Get list of supported platforms.

        Returns:
            List of supported platform names

        Raises:
            httpx.ConnectError: If unable to connect to the service
            httpx.TimeoutException: If the request times out
            httpx.HTTPStatusError: If the server returns an error status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/platforms")
                response.raise_for_status()
                return response.json()["platforms"]
        except httpx.ConnectError as e:
            raise httpx.ConnectError(f"Failed to connect to image extractor service at {self.base_url}: {e}")
        except httpx.TimeoutException as e:
            raise httpx.TimeoutException(f"Request timed out after {self.timeout}s: {e}")
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", "")
            except:
                error_detail = e.response.text
            raise httpx.HTTPStatusError(
                f"HTTP {e.response.status_code} error: {error_detail}",
                request=e.request,
                response=e.response
            )

# Usage in your other apps:
client = ImageExtractorClient()
result = await client.extract_images("https://flickr.com/photos/user/123456")
