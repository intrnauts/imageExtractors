import re
from typing import Dict, List
from .base import BaseExtractor
from ..utils.http_client import get_http_client
from ..utils.validation import validate_flickr_url, validate_extraction_options
from ..config import get_config
from ..exceptions import (
    PlatformNotConfiguredError,
    ExtractionError,
    APIError,
    InvalidURLError,
    wrap_http_error
)
import os

class FlickrExtractor(BaseExtractor):
    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.get_api_key('flickr')
        self.base_url = "https://api.flickr.com/services/rest/"
    
    @property
    def platform_name(self) -> str:
        return "flickr"
    
    @property
    def url_patterns(self) -> List[str]:
        return [
            r'flickr\.com/photos/[^/]+/\d+',
            r'flickr\.com/p/\w+',
            r'flickr\.com/photos/[^/]+/albums/\d+',
            r'flickr\.com/photos/[^/]+/sets/\d+',
        ]
    
    def _extract_photo_id(self, url: str) -> str:
        patterns = [
            r'/photos/[^/]+/(\d+)',
            r'/p/(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _extract_photoset_id(self, url: str) -> str:
        patterns = [
            r'/albums/(\d+)',
            r'/sets/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def extract(self, url: str, options: Dict) -> Dict:
        # Validate API key configuration
        if not self.api_key:
            raise PlatformNotConfiguredError("flickr", "FLICKR_API_KEY")

        # Validate and sanitize inputs
        try:
            url_info = validate_flickr_url(url)
            validated_options = validate_extraction_options(options)
        except Exception as e:
            if isinstance(e, (InvalidURLError, ValidationError)):
                raise e
            raise ExtractionError(url, "flickr", f"Validation failed: {str(e)}")

        try:
            if url_info['type'] == 'photoset':
                return await self._extract_photoset(url_info['id'], validated_options)
            else:  # photo
                return await self._extract_single_photo(url_info['id'], validated_options)

        except Exception as e:
            if isinstance(e, (ExtractionError, APIError)):
                raise e
            # Wrap unexpected errors
            raise ExtractionError(url, "flickr", f"Unexpected error during extraction: {str(e)}")
    
    async def _extract_single_photo(self, photo_id: str, options: Dict) -> Dict:
        try:
            client = await get_http_client('flickr')

            # Get photo info
            info_params = {
                'method': 'flickr.photos.getInfo',
                'api_key': self.api_key,
                'photo_id': photo_id,
                'format': 'json',
                'nojsoncallback': 1
            }

            info_response = await client.get(self.base_url, params=info_params)
            info_data = info_response.json()

            # Get sizes
            sizes_params = {
                'method': 'flickr.photos.getSizes',
                'api_key': self.api_key,
                'photo_id': photo_id,
                'format': 'json',
                'nojsoncallback': 1
            }

            sizes_response = await client.get(self.base_url, params=sizes_params)
            sizes_data = sizes_response.json()

            # Check API responses
            if info_data.get('stat') != 'ok':
                error_msg = info_data.get('message', 'Unknown API error')
                raise APIError(f"photo/{photo_id}", "flickr", {"message": error_msg, "code": info_data.get('code')})

            if sizes_data.get('stat') != 'ok':
                error_msg = sizes_data.get('message', 'Unknown API error')
                raise APIError(f"photo/{photo_id}", "flickr", {"message": error_msg, "code": sizes_data.get('code')})

        except Exception as e:
            if isinstance(e, APIError):
                raise e
            # Wrap HTTP errors
            raise wrap_http_error(e, f"{self.base_url}?photo_id={photo_id}", "photo info retrieval")

        photo_info = info_data['photo']
        sizes = sizes_data['sizes']['size']

        # Convert to our format
        images = []

        for size in sizes:
            images.append({
                'url': size['source'],
                'title': photo_info['title']['_content'],
                'description': photo_info.get('description', {}).get('_content'),
                'width': int(size['width']),
                'height': int(size['height']),
                'size_label': size['label']
            })

        return {
            'platform': self.platform_name,
            'type': 'single',
            'images': images,
            'metadata': {
                'photo_id': photo_id,
                'owner': photo_info['owner']['username'],
                'date_taken': photo_info.get('dates', {}).get('taken')
            }
        }
    
    async def _extract_photoset(self, photoset_id: str, options: Dict) -> Dict:
        client = await get_http_client('flickr')

        # Get photoset info
        info_params = {
            'method': 'flickr.photosets.getInfo',
            'api_key': self.api_key,
            'photoset_id': photoset_id,
            'format': 'json',
            'nojsoncallback': 1
        }

        info_response = await client.get(self.base_url, params=info_params)
        info_data = info_response.json()

        # Get photos in the set
        photos_params = {
            'method': 'flickr.photosets.getPhotos',
            'api_key': self.api_key,
            'photoset_id': photoset_id,
            'format': 'json',
            'nojsoncallback': 1
        }

        photos_response = await client.get(self.base_url, params=photos_params)
        photos_data = photos_response.json()

        if info_data['stat'] != 'ok' or photos_data['stat'] != 'ok':
            raise ValueError("Failed to fetch photoset data from Flickr")

        photoset_info = info_data['photoset']
        photos = photos_data['photoset']['photo']

        # Get image URLs for each photo with improved batching for performance
        images = []

        # Use asyncio.gather for concurrent API calls (with rate limiting handled by client)
        import asyncio

        async def get_photo_sizes(photo):
            """Get sizes for a single photo"""
            sizes_params = {
                'method': 'flickr.photos.getSizes',
                'api_key': self.api_key,
                'photo_id': photo['id'],
                'format': 'json',
                'nojsoncallback': 1
            }

            try:
                sizes_response = await client.get(self.base_url, params=sizes_params)
                sizes_data = sizes_response.json()

                if sizes_data['stat'] == 'ok':
                    sizes = sizes_data['sizes']['size']
                    # Get the largest size available
                    largest = max(sizes, key=lambda x: int(x.get('width', 0)) * int(x.get('height', 0)))

                    return {
                        'url': largest['source'],
                        'title': photo['title'],
                        'width': int(largest['width']),
                        'height': int(largest['height']),
                        'size_label': largest['label']
                    }
            except Exception as e:
                # Log error but continue with other photos
                print(f"Warning: Failed to get sizes for photo {photo['id']}: {e}")
                return None

        # Process photos in batches to avoid overwhelming the API
        batch_size = self.config.extractors.batch_size
        for i in range(0, len(photos), batch_size):
            batch = photos[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[get_photo_sizes(photo) for photo in batch],
                return_exceptions=True
            )

            # Add successful results to images
            for result in batch_results:
                if result and not isinstance(result, Exception):
                    images.append(result)

        return {
            'platform': self.platform_name,
            'type': 'album',
            'images': images,
            'metadata': {
                'photoset_id': photoset_id,
                'title': photoset_info['title']['_content'],
                'description': photoset_info.get('description', {}).get('_content', ''),
                'photo_count': len(images)
            }
        }
