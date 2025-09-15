"""
Advanced FastAPI Integration Patterns for Image Extractor
"""
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, AsyncGenerator
import asyncio
import aioredis
from contextlib import asynccontextmanager
import json
import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to sys.path to import the client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import ImageExtractorClient

# Advanced dependency injection patterns

class ImageExtractorService:
    """Service class with connection pooling and caching"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = ImageExtractorClient(base_url)
        self.redis = None
        self.cache_ttl = 3600  # 1 hour

    async def init_cache(self):
        """Initialize Redis cache"""
        try:
            self.redis = await aioredis.from_url("redis://localhost:6379")
        except Exception as e:
            print(f"Redis not available: {e}")
            self.redis = None

    async def close_cache(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

    async def extract_with_cache(self, url: str, options: Dict = None) -> Dict:
        """Extract with caching support"""
        cache_key = f"extract:{hash(url + str(options or {}))}"

        # Try cache first
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        # Extract images
        result = await self.client.extract_images(url, options)

        # Cache result
        if self.redis:
            try:
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(result, default=str)
                )
            except Exception:
                pass

        return result

# Global service instance
extractor_service = ImageExtractorService()

# Lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    await extractor_service.init_cache()
    print("✓ Image extractor service initialized")

    yield

    # Shutdown
    await extractor_service.close_cache()
    print("✓ Image extractor service closed")

app = FastAPI(
    title="Advanced Image Extractor Integration",
    lifespan=lifespan
)

# Dependency injection patterns

async def get_extractor_service() -> ImageExtractorService:
    """Get the image extractor service"""
    return extractor_service

class ExtractorConfig:
    """Configuration dependency"""
    def __init__(self):
        self.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "10"))
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.rate_limit = int(os.getenv("RATE_LIMIT", "100"))

async def get_config() -> ExtractorConfig:
    """Get configuration"""
    return ExtractorConfig()

# Authentication dependency (optional)
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """Simple token-based auth (replace with your auth logic)"""
    if not credentials:
        return None

    # Simple token validation (use proper JWT/OAuth in production)
    if credentials.credentials == "your-api-token":
        return "authenticated_user"

    return None

# Advanced background task management

class TaskManager:
    """Manage background extraction tasks"""

    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Dict] = {}

    async def start_extraction_task(
        self,
        task_id: str,
        urls: List[str],
        service: ImageExtractorService
    ) -> str:
        """Start a background extraction task"""

        async def extraction_task():
            results = []
            for url in urls:
                try:
                    result = await service.extract_with_cache(url)
                    results.append({
                        'url': url,
                        'success': True,
                        'images': len(result['images']),
                        'platform': result['platform']
                    })
                except Exception as e:
                    results.append({
                        'url': url,
                        'success': False,
                        'error': str(e)
                    })

                # Allow other tasks to run
                await asyncio.sleep(0.1)

            self.task_results[task_id] = {
                'status': 'completed',
                'results': results,
                'completed_at': datetime.now().isoformat()
            }

            # Clean up task reference
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

        task = asyncio.create_task(extraction_task())
        self.active_tasks[task_id] = task

        return task_id

    def get_task_status(self, task_id: str) -> Dict:
        """Get status of a background task"""
        if task_id in self.task_results:
            return self.task_results[task_id]

        if task_id in self.active_tasks:
            return {
                'status': 'running',
                'started_at': datetime.now().isoformat()
            }

        return {'status': 'not_found'}

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            del self.active_tasks[task_id]
            return True
        return False

task_manager = TaskManager()

async def get_task_manager() -> TaskManager:
    """Get task manager dependency"""
    return task_manager

# Pydantic models for advanced patterns

class AsyncExtractionRequest(BaseModel):
    urls: List[str] = Field(..., max_items=50)
    webhook_url: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=5)

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

# Advanced routes

@app.post("/extract-async", response_model=TaskResponse)
async def start_async_extraction(
    request: AsyncExtractionRequest,
    service: ImageExtractorService = Depends(get_extractor_service),
    task_mgr: TaskManager = Depends(get_task_manager),
    user: Optional[str] = Depends(get_current_user)
):
    """Start asynchronous extraction for multiple URLs"""

    # Generate task ID
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(request.urls)) % 10000}"

    # Start background task
    await task_mgr.start_extraction_task(task_id, request.urls, service)

    return TaskResponse(
        task_id=task_id,
        status="started",
        message=f"Processing {len(request.urls)} URLs in background"
    )

@app.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    task_mgr: TaskManager = Depends(get_task_manager)
):
    """Get status of a background task"""
    status = task_mgr.get_task_status(task_id)

    if status['status'] == 'not_found':
        raise HTTPException(status_code=404, detail="Task not found")

    return status

@app.delete("/task/{task_id}")
async def cancel_task(
    task_id: str,
    task_mgr: TaskManager = Depends(get_task_manager)
):
    """Cancel a running task"""
    success = task_mgr.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already completed")

    return {"message": "Task cancelled successfully"}

# Streaming response example
@app.get("/extract-stream")
async def extract_stream(
    urls: List[str],
    service: ImageExtractorService = Depends(get_extractor_service)
):
    """Stream extraction results as they complete"""

    async def generate():
        for i, url in enumerate(urls):
            try:
                result = await service.extract_with_cache(url)
                yield f"data: {json.dumps({'index': i, 'url': url, 'success': True, 'images': len(result['images'])})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'index': i, 'url': url, 'success': False, 'error': str(e)})}\n\n"

            await asyncio.sleep(0.1)  # Small delay for demonstration

        yield f"data: {json.dumps({'status': 'completed'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

# Circuit breaker pattern
class CircuitBreaker:
    """Simple circuit breaker for the extractor service"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""

        if self.state == "open":
            if (datetime.now() - self.last_failure_time).seconds < self.recovery_timeout:
                raise HTTPException(status_code=503, detail="Service temporarily unavailable")
            else:
                self.state = "half-open"

        try:
            result = await func(*args, **kwargs)

            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

            raise e

circuit_breaker = CircuitBreaker()

@app.post("/extract-protected")
async def extract_with_circuit_breaker(
    url: str,
    service: ImageExtractorService = Depends(get_extractor_service)
):
    """Extract with circuit breaker protection"""

    try:
        result = await circuit_breaker.call(
            service.extract_with_cache,
            url
        )

        return {
            'success': True,
            'platform': result['platform'],
            'image_count': len(result['images']),
            'circuit_state': circuit_breaker.state
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check with detailed status
@app.get("/health/detailed")
async def detailed_health_check(
    service: ImageExtractorService = Depends(get_extractor_service)
):
    """Detailed health check including dependencies"""

    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }

    # Check extractor service
    try:
        platforms = await service.client.get_supported_platforms()
        health_status['components']['extractor'] = {
            'status': 'healthy',
            'platforms': len(platforms)
        }
    except Exception as e:
        health_status['components']['extractor'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'

    # Check cache
    if service.redis:
        try:
            await service.redis.ping()
            health_status['components']['cache'] = {'status': 'healthy'}
        except Exception as e:
            health_status['components']['cache'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    else:
        health_status['components']['cache'] = {'status': 'disabled'}

    # Check active tasks
    health_status['components']['background_tasks'] = {
        'active_count': len(task_manager.active_tasks),
        'completed_count': len(task_manager.task_results)
    }

    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)