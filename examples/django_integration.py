"""
Example: Django integration with the Image Extractor
"""

# models.py
from django.db import models

class ExtractedImage(models.Model):
    """Model to store extracted image information"""
    original_url = models.URLField()
    platform = models.CharField(max_length=50)
    image_type = models.CharField(max_length=20)  # single, album
    image_url = models.URLField()
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    width = models.IntegerField(null=True)
    height = models.IntegerField(null=True)
    size_label = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'extracted_images'

# services.py
import asyncio
import sys
import os
from typing import List, Dict

# Add the image extractor to path
sys.path.append('/path/to/imageRxtractors')  # Update this path

from client import ImageExtractorClient
from .models import ExtractedImage

class ImageExtractionService:
    def __init__(self):
        self.client = ImageExtractorClient(base_url="http://localhost:8000")

    async def extract_and_save(self, url: str) -> List[ExtractedImage]:
        """Extract images and save to database"""
        try:
            result = await self.client.extract_images(url)

            images = []
            for img_data in result['images']:
                image = ExtractedImage.objects.create(
                    original_url=url,
                    platform=result['platform'],
                    image_type=result['type'],
                    image_url=img_data['url'],
                    title=img_data.get('title', ''),
                    description=img_data.get('description', ''),
                    width=img_data.get('width'),
                    height=img_data.get('height'),
                    size_label=img_data.get('size_label', ''),
                    metadata=result.get('metadata', {})
                )
                images.append(image)

            return images

        except Exception as e:
            raise Exception(f"Failed to extract images: {str(e)}")

    def sync_extract_and_save(self, url: str) -> List[ExtractedImage]:
        """Synchronous wrapper for Django views"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.extract_and_save(url))
        finally:
            loop.close()

# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["POST"])
def extract_images_view(request):
    """Django view to extract images"""
    try:
        data = json.loads(request.body)
        url = data.get('url')

        if not url:
            return JsonResponse({
                'success': False,
                'error': 'URL is required'
            }, status=400)

        service = ImageExtractionService()
        images = service.sync_extract_and_save(url)

        return JsonResponse({
            'success': True,
            'count': len(images),
            'images': [
                {
                    'id': img.id,
                    'url': img.image_url,
                    'title': img.title,
                    'size': f"{img.width}x{img.height}",
                    'size_label': img.size_label
                }
                for img in images
            ]
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def get_extracted_images_view(request):
    """Get previously extracted images"""
    original_url = request.GET.get('url')

    queryset = ExtractedImage.objects.all()
    if original_url:
        queryset = queryset.filter(original_url=original_url)

    images = queryset.order_by('-created_at')[:50]  # Latest 50

    return JsonResponse({
        'success': True,
        'images': [
            {
                'id': img.id,
                'original_url': img.original_url,
                'platform': img.platform,
                'image_url': img.image_url,
                'title': img.title,
                'size': f"{img.width}x{img.height}" if img.width else "Unknown",
                'created_at': img.created_at.isoformat()
            }
            for img in images
        ]
    })

# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('extract/', views.extract_images_view, name='extract_images'),
    path('images/', views.get_extracted_images_view, name='get_images'),
]

# tasks.py (for Celery background processing)
from celery import shared_task
from .services import ImageExtractionService

@shared_task
def extract_images_async(url: str):
    """Background task to extract images"""
    try:
        service = ImageExtractionService()
        images = service.sync_extract_and_save(url)
        return {
            'success': True,
            'count': len(images),
            'url': url
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'url': url
        }