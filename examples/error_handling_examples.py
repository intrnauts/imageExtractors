"""
Comprehensive error handling examples for Image Extractor integration
"""
import asyncio
import sys
import os
import httpx
from typing import Optional, Dict, List

# Add the parent directory to sys.path to import the client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import ImageExtractorClient

class RobustImageExtractor:
    """
    Wrapper with comprehensive error handling and retry logic
    """
    def __init__(self, base_url: str = "http://localhost:8000", max_retries: int = 3):
        self.client = ImageExtractorClient(base_url)
        self.max_retries = max_retries

    async def extract_with_retry(self, url: str, options: Optional[Dict] = None) -> Optional[Dict]:
        """Extract images with retry logic and detailed error handling"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                print(f"Attempt {attempt + 1}/{self.max_retries} for {url}")

                result = await self.client.extract_images(url, options)
                print(f"✓ Successfully extracted {len(result['images'])} images")
                return result

            except httpx.ConnectError as e:
                last_error = f"Connection failed: {str(e)}"
                print(f"✗ Connection error: {e}")

            except httpx.TimeoutException as e:
                last_error = f"Request timeout: {str(e)}"
                print(f"✗ Timeout error: {e}")

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP error {e.response.status_code}: {e.response.text}"
                print(f"✗ HTTP error: {e.response.status_code}")

                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    break

            except ValueError as e:
                last_error = f"Invalid data: {str(e)}"
                print(f"✗ Value error: {e}")
                break  # Don't retry on validation errors

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                print(f"✗ Unexpected error: {e}")

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)

        print(f"✗ Failed after {self.max_retries} attempts: {last_error}")
        return None

    async def safe_extract(self, url: str) -> Dict:
        """Extract with safe defaults and error information"""
        try:
            result = await self.extract_with_retry(url)

            if result:
                return {
                    'success': True,
                    'data': result,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'data': None,
                    'error': 'Extraction failed after retries'
                }

        except Exception as e:
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }

async def validate_url_before_extraction():
    """Example: Validate URLs before sending to extractor"""
    import re

    def is_valid_url(url: str) -> bool:
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None

    def is_supported_platform(url: str) -> bool:
        """Basic check for known platforms"""
        supported_domains = ['flickr.com', 'imgur.com', 'instagram.com']
        return any(domain in url.lower() for domain in supported_domains)

    test_urls = [
        "https://flickr.com/photos/user/123456",  # Valid
        "not-a-url",  # Invalid
        "https://unsupported-site.com/photo/123",  # Valid URL, unsupported platform
        "http://localhost:8000/test"  # Valid but probably wrong
    ]

    extractor = RobustImageExtractor()

    for url in test_urls:
        print(f"\nValidating: {url}")

        if not is_valid_url(url):
            print("✗ Invalid URL format")
            continue

        if not is_supported_platform(url):
            print("⚠ Warning: URL may not be from a supported platform")

        result = await extractor.safe_extract(url)
        if result['success']:
            print(f"✓ Success: {len(result['data']['images'])} images")
        else:
            print(f"✗ Failed: {result['error']}")

async def handle_service_unavailable():
    """Example: Handle when the extractor service is down"""

    async def check_service_health(base_url: str) -> bool:
        """Check if the extractor service is running"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/health", timeout=5.0)
                return response.status_code == 200
        except:
            return False

    base_url = "http://localhost:8000"

    print("Checking service health...")
    if not await check_service_health(base_url):
        print("✗ Image extractor service is not available")
        print("Possible solutions:")
        print("  1. Start the service: uvicorn main:app --reload")
        print("  2. Check if the service URL is correct")
        print("  3. Use a fallback extraction method")
        return False

    print("✓ Service is healthy")
    return True

async def batch_extraction_with_error_handling():
    """Example: Process multiple URLs with proper error handling"""

    urls = [
        "https://flickr.com/photos/user/123456",
        "https://flickr.com/photos/user/invalid",
        "https://flickr.com/photos/user/789012",
        "invalid-url",
        "https://flickr.com/photos/user/albums/345678"
    ]

    extractor = RobustImageExtractor()

    # Check service first
    if not await handle_service_unavailable():
        return

    results = {
        'successful': [],
        'failed': [],
        'total_images': 0
    }

    print(f"\nProcessing {len(urls)} URLs...")

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")

        result = await extractor.safe_extract(url)

        if result['success']:
            image_count = len(result['data']['images'])
            results['successful'].append({
                'url': url,
                'images': image_count,
                'platform': result['data']['platform']
            })
            results['total_images'] += image_count
            print(f"  ✓ Success: {image_count} images from {result['data']['platform']}")

        else:
            results['failed'].append({
                'url': url,
                'error': result['error']
            })
            print(f"  ✗ Failed: {result['error']}")

    # Summary
    print(f"\n{'='*50}")
    print("BATCH EXTRACTION SUMMARY")
    print(f"{'='*50}")
    print(f"Total URLs processed: {len(urls)}")
    print(f"Successful: {len(results['successful'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Total images extracted: {results['total_images']}")

    if results['failed']:
        print(f"\nFailed URLs:")
        for failed in results['failed']:
            print(f"  - {failed['url']}: {failed['error']}")

async def graceful_degradation_example():
    """Example: Graceful degradation when extractor fails"""

    def fallback_url_parser(url: str) -> Optional[str]:
        """Simple fallback to extract basic image URL from known patterns"""
        import re

        # Very basic Flickr direct image pattern
        flickr_pattern = r'live\.staticflickr\.com/\d+/\d+_\w+_[a-z]\.jpg'
        if re.search(flickr_pattern, url):
            return url

        return None

    url = "https://flickr.com/photos/user/123456"

    print("Attempting extraction with full extractor...")

    extractor = RobustImageExtractor()
    result = await extractor.safe_extract(url)

    if result['success']:
        print("✓ Full extraction successful")
        return result['data']

    print("✗ Full extraction failed, trying fallback...")

    # Try fallback method
    fallback_url = fallback_url_parser(url)
    if fallback_url:
        print(f"✓ Fallback found direct image URL: {fallback_url}")
        return {
            'platform': 'unknown',
            'type': 'single',
            'images': [{'url': fallback_url, 'title': 'Fallback image'}],
            'metadata': {'source': 'fallback'}
        }

    print("✗ No fallback available")
    return None

if __name__ == "__main__":
    print("Image Extractor Error Handling Examples")
    print("=" * 50)

    # Run examples
    asyncio.run(validate_url_before_extraction())
    print("\n" + "-" * 50 + "\n")

    asyncio.run(batch_extraction_with_error_handling())
    print("\n" + "-" * 50 + "\n")

    asyncio.run(graceful_degradation_example())