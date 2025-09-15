"""
FastAPI Integration Examples for Image Extractor
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Union
import asyncio
import httpx
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to import the client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import ImageExtractorClient

# Pydantic models for request/response
class ImageExtractionRequest(BaseModel):
    url: HttpUrl
    size_filter: Optional[str] = Field(None, description="Filter by image size (e.g., 'Large', 'Medium')")
    download_largest: bool = Field(False, description="Download and return the largest image URL")

class ImageInfo(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_label: Optional[str] = None

class ExtractionResponse(BaseModel):
    success: bool
    platform: Optional[str] = None
    type: Optional[str] = None
    images: List[ImageInfo] = []
    metadata: Dict = {}
    total_images: int = 0
    filtered_images: int = 0
    processing_time_ms: float = 0

class BatchExtractionRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., max_items=10, description="Maximum 10 URLs per batch")
    size_filter: Optional[str] = None

class BatchExtractionResponse(BaseModel):
    success: bool
    results: List[Dict] = []
    total_urls: int = 0
    successful: int = 0
    failed: int = 0
    total_images: int = 0

# FastAPI app
app = FastAPI(
    title="My App with Image Extraction",
    description="Your FastAPI app integrated with image extraction service",
    version="1.0.0"
)

# Dependency for image extractor client
async def get_image_extractor() -> ImageExtractorClient:
    """Dependency injection for image extractor client"""
    return ImageExtractorClient(base_url="http://localhost:8000")

# Health check for the image extractor service
async def check_extractor_health(client: ImageExtractorClient) -> bool:
    """Check if the extractor service is healthy"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(f"{client.base_url}/health", timeout=5.0)
            return response.status_code == 200
    except:
        return False

# Routes

@app.post("/extract-images", response_model=ExtractionResponse)
async def extract_images(
    request: ImageExtractionRequest,
    client: ImageExtractorClient = Depends(get_image_extractor)
):
    """Extract images from a URL with optional filtering"""
    start_time = datetime.now()

    try:
        # Check service health first
        if not await check_extractor_health(client):
            raise HTTPException(
                status_code=503,
                detail="Image extraction service is unavailable"
            )

        # Extract images
        result = await client.extract_images(str(request.url))

        # Apply size filter if specified
        filtered_images = result['images']
        if request.size_filter:
            filtered_images = [
                img for img in result['images']
                if request.size_filter.lower() in img.get('size_label', '').lower()
            ]

        # Convert to Pydantic models
        image_infos = [
            ImageInfo(
                url=img['url'],
                title=img.get('title'),
                description=img.get('description'),
                width=img.get('width'),
                height=img.get('height'),
                size_label=img.get('size_label')
            )
            for img in filtered_images
        ]

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ExtractionResponse(
            success=True,
            platform=result['platform'],
            type=result['type'],
            images=image_infos,
            metadata=result.get('metadata', {}),
            total_images=len(result['images']),
            filtered_images=len(filtered_images),
            processing_time_ms=round(processing_time, 2)
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Extraction service error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-extract", response_model=BatchExtractionResponse)
async def batch_extract_images(
    request: BatchExtractionRequest,
    background_tasks: BackgroundTasks,
    client: ImageExtractorClient = Depends(get_image_extractor)
):
    """Extract images from multiple URLs"""

    # Check service health
    if not await check_extractor_health(client):
        raise HTTPException(
            status_code=503,
            detail="Image extraction service is unavailable"
        )

    results = []
    successful = 0
    total_images = 0

    for url in request.urls:
        try:
            result = await client.extract_images(str(url))

            # Apply filter if specified
            images = result['images']
            if request.size_filter:
                images = [
                    img for img in images
                    if request.size_filter.lower() in img.get('size_label', '').lower()
                ]

            results.append({
                'url': str(url),
                'success': True,
                'platform': result['platform'],
                'type': result['type'],
                'image_count': len(images),
                'images': images[:5],  # Limit to first 5 for response size
                'error': None
            })

            successful += 1
            total_images += len(images)

        except Exception as e:
            results.append({
                'url': str(url),
                'success': False,
                'platform': None,
                'type': None,
                'image_count': 0,
                'images': [],
                'error': str(e)
            })

    return BatchExtractionResponse(
        success=True,
        results=results,
        total_urls=len(request.urls),
        successful=successful,
        failed=len(request.urls) - successful,
        total_images=total_images
    )

@app.get("/extract-largest")
async def extract_largest_image(
    url: HttpUrl = Query(..., description="URL to extract from"),
    client: ImageExtractorClient = Depends(get_image_extractor)
):
    """Extract and return only the largest image"""
    try:
        result = await client.extract_images(str(url))

        if not result['images']:
            raise HTTPException(status_code=404, detail="No images found")

        # Find largest image
        largest = max(
            result['images'],
            key=lambda x: (x.get('width', 0) * x.get('height', 0))
        )

        return {
            'success': True,
            'url': str(url),
            'platform': result['platform'],
            'largest_image': {
                'url': largest['url'],
                'title': largest.get('title'),
                'width': largest.get('width'),
                'height': largest.get('height'),
                'size_label': largest.get('size_label'),
                'pixels': largest.get('width', 0) * largest.get('height', 0)
            },
            'total_available': len(result['images']),
            'metadata': result.get('metadata', {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/supported-platforms")
async def get_supported_platforms(
    client: ImageExtractorClient = Depends(get_image_extractor)
):
    """Get list of supported platforms"""
    try:
        platforms = await client.get_supported_platforms()
        return {
            'success': True,
            'platforms': platforms,
            'count': len(platforms)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background task example
async def log_extraction_stats(url: str, result: Dict):
    """Background task to log extraction statistics"""
    # This could save to database, send to analytics, etc.
    print(f"STATS: {url} -> {result['platform']} -> {len(result['images'])} images")

@app.post("/extract-with-logging")
async def extract_with_background_logging(
    request: ImageExtractionRequest,
    background_tasks: BackgroundTasks,
    client: ImageExtractorClient = Depends(get_image_extractor)
):
    """Extract images and log stats in background"""
    try:
        result = await client.extract_images(str(request.url))

        # Add background task for logging
        background_tasks.add_task(log_extraction_stats, str(request.url), result)

        return {
            'success': True,
            'platform': result['platform'],
            'image_count': len(result['images']),
            'message': 'Extraction completed, stats logged in background'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Middleware example for automatic retry
@app.middleware("http")
async def retry_middleware(request, call_next):
    """Middleware to add retry logic for specific endpoints"""
    max_retries = 2

    # Only apply retry to extraction endpoints
    if request.url.path.startswith("/extract"):
        for attempt in range(max_retries + 1):
            try:
                response = await call_next(request)
                if response.status_code < 500:  # Don't retry client errors
                    return response
                if attempt == max_retries:
                    return response
                await asyncio.sleep(1)  # Wait before retry
            except Exception as e:
                if attempt == max_retries:
                    raise e
                await asyncio.sleep(1)
    else:
        response = await call_next(request)

    return response

# Custom dependency for rate limiting (example)
class RateLimiter:
    def __init__(self, max_requests: int = 100):
        self.max_requests = max_requests
        self.requests = {}

    async def __call__(self, request):
        client_ip = request.client.host
        current_time = datetime.now()

        # Simple rate limiting logic (in production, use Redis)
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Remove old requests (older than 1 hour)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if (current_time - req_time).seconds < 3600
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        self.requests[client_ip].append(current_time)
        return True

rate_limiter = RateLimiter(max_requests=50)

@app.post("/extract-rate-limited")
async def extract_with_rate_limit(
    request: ImageExtractionRequest,
    client: ImageExtractorClient = Depends(get_image_extractor),
    _: bool = Depends(rate_limiter)
):
    """Extract images with rate limiting"""
    try:
        result = await client.extract_images(str(request.url))
        return {
            'success': True,
            'platform': result['platform'],
            'image_count': len(result['images'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Custom exception handler
@app.exception_handler(httpx.ConnectError)
async def connection_error_handler(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            'success': False,
            'error': 'Image extraction service is unavailable',
            'detail': 'Please try again later'
        }
    )

# Startup event to check extractor service
@app.on_event("startup")
async def startup_event():
    """Check if image extractor service is available on startup"""
    client = ImageExtractorClient()
    if await check_extractor_health(client):
        print("✓ Image extraction service is available")
    else:
        print("⚠ Warning: Image extraction service is not available")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)