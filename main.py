# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List
import os
from extractors import ExtractorRegistry

app = FastAPI(
    title="Image URL Extraction Service",
    description="Extract direct image URLs from various hosting platforms",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize extractor registry
registry = ExtractorRegistry()

class ExtractRequest(BaseModel):
    url: HttpUrl
    options: Optional[Dict] = {}

class ImageInfo(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_label: Optional[str] = None

class ExtractResponse(BaseModel):
    platform: str
    type: str  # 'single', 'album', 'gallery'
    images: List[ImageInfo]
    metadata: Optional[Dict] = {}

@app.post("/extract", response_model=ExtractResponse)
async def extract_images(request: ExtractRequest):
    try:
        extractor = registry.get_extractor(str(request.url))
        if not extractor:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported platform or invalid URL"
            )
        
        result = await extractor.extract(str(request.url), request.options)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/platforms")
async def get_supported_platforms():
    """Return list of supported platforms"""
    return {"platforms": registry.get_supported_platforms()}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
