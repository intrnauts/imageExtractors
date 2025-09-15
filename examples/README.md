# Image Extractor Integration Examples

This directory contains comprehensive examples of how to integrate the Image Extractor in various applications and scenarios.

## Examples Overview

### 1. `integration_examples.py`
Basic usage patterns and integration examples:
- Simple extraction
- Downloading images
- Batch processing
- Size filtering
- Wrapper class for easier integration

**Usage:**
```bash
cd examples/
python integration_examples.py
```

### 2. `fastapi_simple_integration.py` ⭐ **RECOMMENDED FOR FASTAPI APPS**
Simple FastAPI integration - easy copy-paste for your existing app:
- Basic extraction endpoints
- Dependency injection
- User-specific extraction
- Clean, minimal code

**Usage:**
```bash
python fastapi_simple_integration.py
# Visit http://localhost:8001/docs for API documentation
```

### 3. `fastapi_integration.py`
Full-featured FastAPI integration:
- Comprehensive Pydantic models
- Batch processing
- Background tasks
- Rate limiting
- Middleware examples
- Advanced error handling

**Usage:**
```bash
python fastapi_integration.py
# Visit http://localhost:8001/docs for API documentation
```

### 4. `fastapi_advanced_patterns.py`
Production-ready FastAPI patterns:
- Dependency injection with service classes
- Redis caching
- Background task management
- Circuit breaker pattern
- Streaming responses
- Authentication
- Health checks

**Usage:**
```bash
pip install aioredis
python fastapi_advanced_patterns.py
```

### 5. `web_app_integration.py`
Flask web application integration:
- REST API endpoints
- Image downloading
- Platform listing
- Error handling in web context

**Usage:**
```bash
pip install flask
python web_app_integration.py
```

### 6. `django_integration.py`
Django framework integration:
- Model for storing extracted images
- Service class for extraction
- Views and URL patterns
- Celery background tasks

**Setup:**
1. Add to your Django project
2. Run migrations: `python manage.py makemigrations && python manage.py migrate`
3. Update the path to your image extractor

### 7. `error_handling_examples.py`
Comprehensive error handling patterns:
- Retry logic with exponential backoff
- URL validation
- Service health checks
- Batch processing with error reporting
- Graceful degradation

**Usage:**
```bash
python error_handling_examples.py
```

## Quick Start

### 1. Start the Image Extractor Service
```bash
# In the main directory
uvicorn main:app --reload
```

### 2. Basic Integration
```python
from client import ImageExtractorClient

client = ImageExtractorClient()
result = await client.extract_images("https://flickr.com/photos/user/123456")

print(f"Found {len(result['images'])} images")
for img in result['images']:
    print(f"  {img['size_label']}: {img['url']}")
```

### 3. With Error Handling
```python
from examples.error_handling_examples import RobustImageExtractor

extractor = RobustImageExtractor()
result = await extractor.safe_extract(url)

if result['success']:
    print(f"Success: {len(result['data']['images'])} images")
else:
    print(f"Failed: {result['error']}")
```

## Common Integration Patterns

### 1. Wrapper Class Pattern
Use the `ImageExtractorWrapper` class for simplified integration:

```python
wrapper = ImageExtractorWrapper()

# Get only large images
large_urls = await wrapper.get_image_urls(url, "Large")

# Check if it's an album
is_album = await wrapper.is_album(url)

# Get metadata only
metadata = await wrapper.get_metadata(url)
```

### 2. Async/Sync Bridge
For synchronous frameworks (Django, Flask):

```python
import asyncio

def sync_extract_images(url: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(client.extract_images(url))
    finally:
        loop.close()
```

### 3. Batch Processing
```python
urls = ["url1", "url2", "url3"]
results = []

for url in urls:
    try:
        result = await client.extract_images(url)
        results.append({'url': url, 'result': result, 'error': None})
    except Exception as e:
        results.append({'url': url, 'result': None, 'error': str(e)})
```

## Error Handling Best Practices

1. **Always validate URLs** before sending to the extractor
2. **Implement retry logic** for network failures
3. **Check service health** before processing
4. **Use timeouts** to avoid hanging requests
5. **Provide fallback mechanisms** when possible
6. **Log errors** with sufficient detail for debugging

## Environment Setup

Make sure your image extractor service is configured:

```bash
# Copy environment file
cp .env.example .env

# Edit with your API keys
nano .env
```

Required environment variables:
- `FLICKR_API_KEY`: Your Flickr API key

## Dependencies

For the examples, you may need additional packages:

```bash
# For web app integration
pip install flask

# For Django integration
pip install django celery

# For enhanced HTTP client
pip install httpx[http2]
```

## Troubleshooting

### Service Connection Issues
```python
# Check if service is running
async def check_health():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            return response.status_code == 200
    except:
        return False
```

### API Key Issues
- Ensure `FLICKR_API_KEY` is set in your environment
- Test API key with Flickr's API explorer
- Check rate limits and quotas

### URL Format Issues
- Use full URLs with protocol (https://)
- Ensure URLs match the supported patterns
- Test with known working URLs first