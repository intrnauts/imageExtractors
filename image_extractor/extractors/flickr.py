import httpx
import re
from typing import Dict, List
from .base import BaseExtractor
import os

class FlickrExtractor(BaseExtractor):
    def __init__(self):
        self.api_key = os.getenv('FLICKR_API_KEY')
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
        if not self.api_key:
            raise ValueError("Flickr API key not configured")
        
        # Check for photoset/album
        photoset_id = self._extract_photoset_id(url)
        if photoset_id:
            return await self._extract_photoset(photoset_id, options)
        
        # Single photo
        photo_id = self._extract_photo_id(url)
        if photo_id:
            return await self._extract_single_photo(photo_id, options)
        
        raise ValueError("Could not extract Flickr ID from URL")
    
    async def _extract_single_photo(self, photo_id: str, options: Dict) -> Dict:
        async with httpx.AsyncClient() as client:
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
            
            if info_data['stat'] != 'ok' or sizes_data['stat'] != 'ok':
                raise ValueError("Failed to fetch photo data from Flickr")
            
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
        async with httpx.AsyncClient() as client:
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
            
            # Get image URLs for each photo (simplified - just get one size per photo)
            images = []
            for photo in photos:
                # Get sizes for this photo
                sizes_params = {
                    'method': 'flickr.photos.getSizes',
                    'api_key': self.api_key,
                    'photo_id': photo['id'],
                    'format': 'json',
                    'nojsoncallback': 1
                }
                
                sizes_response = await client.get(self.base_url, params=sizes_params)
                sizes_data = sizes_response.json()
                
                if sizes_data['stat'] == 'ok':
                    sizes = sizes_data['sizes']['size']
                    # Get the largest size available
                    largest = max(sizes, key=lambda x: int(x.get('width', 0)) * int(x.get('height', 0)))
                    
                    images.append({
                        'url': largest['source'],
                        'title': photo['title'],
                        'width': int(largest['width']),
                        'height': int(largest['height']),
                        'size_label': largest['label']
                    })
            
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
