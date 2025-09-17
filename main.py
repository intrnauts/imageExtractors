# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, ValidationError as PydanticValidationError
from typing import Optional, Dict, List
import os
import logging
from image_extractor.extractors import ExtractorRegistry
from image_extractor.exceptions import (
    ImageExtractorError,
    PlatformNotConfiguredError,
    UnsupportedPlatformError,
    InvalidURLError,
    ValidationError,
    create_user_friendly_error
)
from image_extractor.utils.validation import validate_url, sanitize_url
from image_extractor.config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Initialize extractor registry and validate configuration
try:
    config = get_config()
    logger.info("Configuration loaded successfully")
    registry = ExtractorRegistry()
    logger.info(f"Initialized extractors for platforms: {registry.get_supported_platforms()}")
except Exception as e:
    logger.error(f"Failed to initialize application: {e}")
    raise

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

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict] = {}
    user_message: str


# Exception handlers
@app.exception_handler(ImageExtractorError)
async def image_extractor_error_handler(request: Request, exc: ImageExtractorError):
    logger.warning(f"ImageExtractorError: {exc.message}", extra={"details": exc.details})

    status_code = 400
    if isinstance(exc, PlatformNotConfiguredError):
        status_code = 503  # Service Unavailable
    elif isinstance(exc, UnsupportedPlatformError):
        status_code = 400  # Bad Request
    elif isinstance(exc, (InvalidURLError, ValidationError)):
        status_code = 422  # Unprocessable Entity

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "user_message": create_user_friendly_error(exc)
        }
    )


@app.exception_handler(PydanticValidationError)
async def validation_error_handler(request: Request, exc: PydanticValidationError):
    logger.warning(f"Validation error: {exc}")

    # Extract field names and error messages
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")

    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Input validation failed",
            "details": {"validation_errors": errors},
            "user_message": f"📝 Invalid input: {'; '.join(errors)}"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": {"error_type": exc.__class__.__name__},
            "user_message": "❌ An unexpected error occurred. Please try again later."
        }
    )

@app.post("/extract", response_model=ExtractResponse, responses={
    400: {"model": ErrorResponse, "description": "Invalid URL or unsupported platform"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    503: {"model": ErrorResponse, "description": "Platform not configured"},
    500: {"model": ErrorResponse, "description": "Internal server error"}
})
async def extract_images(request: ExtractRequest):
    """
    Extract images from a supported platform URL.

    This endpoint accepts a URL from a supported platform (Flickr, etc.) and returns
    direct image URLs along with metadata. The service handles rate limiting and
    provides detailed error messages for debugging.
    """
    url = sanitize_url(str(request.url))
    logger.info(f"Extracting images from: {url}")

    # Find appropriate extractor
    extractor = registry.get_extractor(url)
    if not extractor:
        supported_platforms = registry.get_supported_platforms()
        raise UnsupportedPlatformError(url, supported_platforms)

    logger.info(f"Using {extractor.platform_name} extractor")

    # Extract images
    result = await extractor.extract(url, request.options)

    logger.info(f"Successfully extracted {len(result['images'])} images from {extractor.platform_name}")
    return result

@app.get("/platforms")
async def get_supported_platforms():
    """
    Get list of supported platforms and their configuration status.

    Returns information about which platforms are available and properly configured.
    """
    platforms = registry.get_supported_platforms()
    platform_status = {}

    for platform in platforms:
        is_configured = config.is_platform_configured(platform)
        platform_status[platform] = {
            "available": True,
            "configured": is_configured,
            "status": "ready" if is_configured else "needs_configuration"
        }

    return {
        "platforms": platforms,
        "platform_status": platform_status,
        "total_configured": sum(1 for status in platform_status.values() if status["configured"])
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint with detailed system status.

    Returns the health status of the service including configuration validation.
    """
    try:
        # Check configuration
        config.validate()

        # Check extractor availability
        platforms = registry.get_supported_platforms()
        configured_platforms = [p for p in platforms if config.is_platform_configured(p)]

        health_status = {
            "status": "healthy",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "configuration": {
                "valid": True,
                "platforms_available": len(platforms),
                "platforms_configured": len(configured_platforms),
                "configured_platforms": configured_platforms
            },
            "dependencies": {
                "http_client": "ready",
                "rate_limiter": "ready"
            }
        }

        if len(configured_platforms) == 0:
            health_status["status"] = "degraded"
            health_status["warnings"] = ["No platforms are configured with API keys"]

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
                "error": str(e),
                "user_message": create_user_friendly_error(e)
            }
        )
