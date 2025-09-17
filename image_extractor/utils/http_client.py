"""
HTTP client utilities with connection pooling and rate limiting.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
import httpx
from asyncio_throttle import Throttler
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..config import get_config


class RateLimitedHTTPClient:
    """
    HTTP client with rate limiting and connection pooling.

    Features:
    - Connection pooling for efficient resource usage
    - Rate limiting per domain to respect API limits
    - Automatic retry with exponential backoff
    - Configurable timeouts and limits
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0,
        rate_limits: Optional[Dict[str, float]] = None
    ):
        """
        Initialize the rate-limited HTTP client.

        Args:
            max_connections: Maximum number of connections in the pool
            max_keepalive_connections: Maximum number of keep-alive connections
            keepalive_expiry: Time to keep connections alive (seconds)
            timeout: Default timeout for requests (seconds)
            rate_limits: Dict mapping domain to requests per second limit
        """
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.timeout = timeout

        # Default rate limits for common APIs
        default_rate_limits = {
            'api.flickr.com': 1.0,  # 1 request per second for Flickr
            'api.imgur.com': 2.0,   # 2 requests per second for Imgur
            'graph.instagram.com': 1.0,  # 1 request per second for Instagram
        }

        if rate_limits:
            default_rate_limits.update(rate_limits)

        self.rate_limits = default_rate_limits
        self.throttlers: Dict[str, Throttler] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    limits = httpx.Limits(
                        max_connections=self.max_connections,
                        max_keepalive_connections=self.max_keepalive_connections,
                        keepalive_expiry=self.keepalive_expiry
                    )

                    timeout = httpx.Timeout(self.timeout)

                    self._client = httpx.AsyncClient(
                        limits=limits,
                        timeout=timeout,
                        follow_redirects=True
                    )

        return self._client

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return 'default'

    async def _get_throttler(self, domain: str) -> Throttler:
        """Get or create a throttler for the domain."""
        if domain not in self.throttlers:
            rate_limit = self.rate_limits.get(domain, 2.0)  # Default 2 requests/second
            self.throttlers[domain] = Throttler(rate_limit=rate_limit)

        return self.throttlers[domain]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPStatusError: For HTTP error status codes
            httpx.TimeoutException: For request timeouts
            httpx.ConnectError: For connection errors
        """
        client = await self._get_client()
        domain = self._get_domain(url)
        throttler = await self._get_throttler(domain)

        # Apply rate limiting
        async with throttler:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request."""
        return await self.request('GET', url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request."""
        return await self.request('POST', url, **kwargs)

    async def close(self):
        """Close the HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

        # Clear throttlers
        self.throttlers.clear()

    @asynccontextmanager
    async def session(self):
        """Context manager for handling client lifecycle."""
        try:
            yield self
        finally:
            await self.close()


class HTTPClientManager:
    """
    Singleton manager for HTTP clients to share connection pools across extractors.
    """

    _instance: Optional['HTTPClientManager'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._clients: Dict[str, RateLimitedHTTPClient] = {}
        self._default_client: Optional[RateLimitedHTTPClient] = None

    @classmethod
    async def get_instance(cls) -> 'HTTPClientManager':
        """Get singleton instance of HTTPClientManager."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def get_client(
        self,
        name: str = 'default',
        **client_kwargs
    ) -> RateLimitedHTTPClient:
        """
        Get or create a named HTTP client.

        Args:
            name: Client name for identification
            **client_kwargs: Arguments for RateLimitedHTTPClient

        Returns:
            RateLimitedHTTPClient instance
        """
        if name not in self._clients:
            self._clients[name] = RateLimitedHTTPClient(**client_kwargs)

        return self._clients[name]

    async def get_default_client(self) -> RateLimitedHTTPClient:
        """Get the default HTTP client."""
        if self._default_client is None:
            # Use configuration for defaults
            config = get_config()

            self._default_client = RateLimitedHTTPClient(
                max_connections=config.http.max_connections,
                max_keepalive_connections=config.http.max_keepalive_connections,
                keepalive_expiry=config.http.keepalive_expiry,
                timeout=config.http.timeout,
                rate_limits=config.rate_limits.to_dict()
            )

        return self._default_client

    async def close_all(self):
        """Close all HTTP clients."""
        for client in self._clients.values():
            await client.close()

        if self._default_client:
            await self._default_client.close()
            self._default_client = None

        self._clients.clear()


# Global function for easy access
async def get_http_client(name: str = 'default', **kwargs) -> RateLimitedHTTPClient:
    """
    Get a rate-limited HTTP client.

    Args:
        name: Client name
        **kwargs: Client configuration

    Returns:
        RateLimitedHTTPClient instance
    """
    manager = await HTTPClientManager.get_instance()
    if name == 'default' and not kwargs:
        return await manager.get_default_client()
    else:
        return await manager.get_client(name, **kwargs)