"""
Examples of how to integrate the Image Extractor in other applications
"""
import asyncio
import sys
import os

# Add the parent directory to sys.path to import the client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import ImageExtractorClient

async def basic_usage():
    """Basic usage example"""
    client = ImageExtractorClient(base_url="http://localhost:8000")

    try:
        # Extract from a single Flickr photo
        result = await client.extract_images("https://flickr.com/photos/user/123456")

        print(f"Platform: {result['platform']}")
        print(f"Type: {result['type']}")
        print(f"Found {len(result['images'])} image(s)")

        for img in result['images']:
            print(f"  - {img['size_label']}: {img['url']} ({img['width']}x{img['height']})")

    except Exception as e:
        print(f"Error: {e}")

async def download_largest_image():
    """Example: Download the largest available image"""
    import httpx

    client = ImageExtractorClient()

    try:
        result = await client.extract_images("https://flickr.com/photos/user/123456")

        if result['images']:
            # Find the largest image
            largest = max(result['images'],
                         key=lambda x: x['width'] * x['height'])

            print(f"Downloading largest image: {largest['size_label']} ({largest['width']}x{largest['height']})")

            # Download the image
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(largest['url'])

                if response.status_code == 200:
                    filename = f"downloaded_image_{largest['width']}x{largest['height']}.jpg"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    print(f"Saved as: {filename}")
                else:
                    print(f"Failed to download: {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")

async def batch_extraction():
    """Example: Extract from multiple URLs"""
    urls = [
        "https://flickr.com/photos/user/123456",
        "https://flickr.com/photos/user/789012",
        "https://flickr.com/photos/user/albums/345678"
    ]

    client = ImageExtractorClient()

    results = []
    for url in urls:
        try:
            result = await client.extract_images(url)
            results.append({'url': url, 'result': result, 'error': None})
            print(f"✓ {url}: {len(result['images'])} images")
        except Exception as e:
            results.append({'url': url, 'result': None, 'error': str(e)})
            print(f"✗ {url}: {e}")

    return results

async def get_specific_size():
    """Example: Get a specific image size"""
    client = ImageExtractorClient()

    try:
        result = await client.extract_images("https://flickr.com/photos/user/123456")

        # Look for medium size images
        medium_images = [img for img in result['images']
                        if 'Medium' in img.get('size_label', '')]

        if medium_images:
            print("Medium size images found:")
            for img in medium_images:
                print(f"  {img['size_label']}: {img['url']}")
        else:
            print("No medium size images found. Available sizes:")
            for img in result['images']:
                print(f"  {img['size_label']}: {img['width']}x{img['height']}")

    except Exception as e:
        print(f"Error: {e}")

async def check_supported_platforms():
    """Example: Check what platforms are supported"""
    client = ImageExtractorClient()

    try:
        platforms = await client.get_supported_platforms()
        print("Supported platforms:")
        for platform in platforms:
            print(f"  - {platform}")
    except Exception as e:
        print(f"Error: {e}")

class ImageExtractorWrapper:
    """
    Example: Wrapper class for easier integration in your application
    """
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = ImageExtractorClient(base_url)

    async def get_image_urls(self, url: str, size_preference: str = "Large") -> list:
        """Get just the URLs for a preferred size"""
        try:
            result = await self.client.extract_images(url)

            # Filter by size preference
            preferred = [img for img in result['images']
                        if size_preference in img.get('size_label', '')]

            if preferred:
                return [img['url'] for img in preferred]

            # Fall back to all images if preferred size not found
            return [img['url'] for img in result['images']]

        except Exception:
            return []

    async def get_metadata(self, url: str) -> dict:
        """Get just the metadata"""
        try:
            result = await self.client.extract_images(url)
            return result.get('metadata', {})
        except Exception:
            return {}

    async def is_album(self, url: str) -> bool:
        """Check if URL points to an album/gallery"""
        try:
            result = await self.client.extract_images(url)
            return result.get('type') == 'album'
        except Exception:
            return False

async def using_wrapper_class():
    """Example: Using the wrapper class"""
    wrapper = ImageExtractorWrapper()

    url = "https://flickr.com/photos/user/123456"

    # Get large images only
    large_urls = await wrapper.get_image_urls(url, "Large")
    print(f"Large image URLs: {large_urls}")

    # Get metadata
    metadata = await wrapper.get_metadata(url)
    print(f"Metadata: {metadata}")

    # Check if it's an album
    is_album = await wrapper.is_album(url)
    print(f"Is album: {is_album}")

if __name__ == "__main__":
    print("Image Extractor Integration Examples")
    print("=" * 40)

    # Run examples
    asyncio.run(basic_usage())
    print("\n" + "-" * 40 + "\n")

    asyncio.run(check_supported_platforms())
    print("\n" + "-" * 40 + "\n")

    asyncio.run(using_wrapper_class())