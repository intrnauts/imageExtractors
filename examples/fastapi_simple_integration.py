"""
Simple FastAPI Integration - Easy copy-paste for your existing app
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import sys
import os

# Add the parent directory to sys.path to import the client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import ImageExtractorClient

# Simple models
class ExtractRequest(BaseModel):
    url: HttpUrl
    size_filter: Optional[str] = None  # "Large", "Medium", "Small", etc.

# Dependency - create once, reuse everywhere
async def get_image_client():
    """Get image extractor client"""
    return ImageExtractorClient(base_url="http://localhost:8000")

# Add these routes to your existing FastAPI app
app = FastAPI()

@app.post("/api/extract-images")
async def extract_images(
    request: ExtractRequest,
    client: ImageExtractorClient = Depends(get_image_client)
):
    """
    Extract images from Flickr URLs

    Example request:
    {
        "url": "https://flickr.com/photos/user/123456",
        "size_filter": "Large"
    }
    """
    try:
        # Extract images
        result = await client.extract_images(str(request.url))

        # Filter by size if requested
        images = result['images']
        if request.size_filter:
            images = [
                img for img in images
                if request.size_filter.lower() in img.get('size_label', '').lower()
            ]

        return {
            "success": True,
            "platform": result['platform'],
            "type": result['type'],
            "images": images,
            "total_found": len(result['images']),
            "filtered_count": len(images)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/image-platforms")
async def get_platforms(client: ImageExtractorClient = Depends(get_image_client)):
    """Get supported platforms"""
    try:
        platforms = await client.get_supported_platforms()
        return {"platforms": platforms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/extract-largest")
async def extract_largest(
    url: HttpUrl,
    client: ImageExtractorClient = Depends(get_image_client)
):
    """Get just the largest image from a URL"""
    try:
        result = await client.extract_images(str(url))

        if not result['images']:
            raise HTTPException(status_code=404, detail="No images found")

        # Find largest image
        largest = max(result['images'],
                     key=lambda x: x.get('width', 0) * x.get('height', 0))

        return {
            "success": True,
            "image": {
                "url": largest['url'],
                "title": largest.get('title'),
                "width": largest.get('width'),
                "height": largest.get('height'),
                "size_label": largest.get('size_label')
            },
            "platform": result['platform']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Example: Integration with your existing user system
@app.post("/api/users/{user_id}/extract-images")
async def extract_for_user(
    user_id: int,
    request: ExtractRequest,
    client: ImageExtractorClient = Depends(get_image_client)
):
    """Extract images for a specific user (example integration)"""
    try:
        # You can add user validation here
        # user = await get_user(user_id)
        # if not user:
        #     raise HTTPException(status_code=404, detail="User not found")

        result = await client.extract_images(str(request.url))

        # Here you could save to your database
        # await save_user_images(user_id, result['images'])

        return {
            "success": True,
            "user_id": user_id,
            "url": str(request.url),
            "images_found": len(result['images']),
            "platform": result['platform']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting FastAPI app with image extraction...")
    print("📖 API docs will be available at: http://localhost:8001/docs")
    print("\n🔗 Example usage:")
    print("POST /api/extract-images")
    print('  {"url": "https://flickr.com/photos/user/123456"}')

    uvicorn.run(app, host="0.0.0.0", port=8001)