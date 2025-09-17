# client.py
from typing import Dict, List, Optional
from .utils.http_client import get_http_client

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
            client = await get_http_client('image_extractor_client', timeout=self.timeout)
            response = await client.post(
                f"{self.base_url}/extract",
                json={"url": url, "options": options or {}},
                headers={"Content-Type": "application/json"}
            )
            return response.json()
        except Exception as e:
            # Re-raise with appropriate error types for backward compatibility
            import httpx
            if "connect" in str(e).lower():
                raise httpx.ConnectError(f"Failed to connect to image extractor service at {self.base_url}: {e}")
            elif "timeout" in str(e).lower():
                raise httpx.TimeoutException(f"Request timed out after {self.timeout}s: {e}")
            elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
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
            else:
                raise e
    
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
            client = await get_http_client('image_extractor_client', timeout=self.timeout)
            response = await client.get(f"{self.base_url}/platforms")
            return response.json()["platforms"]
        except Exception as e:
            # Re-raise with appropriate error types for backward compatibility
            import httpx
            if "connect" in str(e).lower():
                raise httpx.ConnectError(f"Failed to connect to image extractor service at {self.base_url}: {e}")
            elif "timeout" in str(e).lower():
                raise httpx.TimeoutException(f"Request timed out after {self.timeout}s: {e}")
            elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
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
            else:
                raise e

# Usage in your other apps:
# client = ImageExtractorClient()
# result = await client.extract_images("https://flickr.com/photos/user/123456")
