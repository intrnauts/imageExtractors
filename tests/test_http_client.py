import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock
from image_extractor.utils.http_client import RateLimitedHTTPClient, HTTPClientManager, get_http_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limited_client_initialization():
    """Test rate limited client initialization"""
    client = RateLimitedHTTPClient(
        max_connections=50,
        timeout=15.0,
        rate_limits={'example.com': 2.0}
    )

    assert client.max_connections == 50
    assert client.timeout == 15.0
    assert client.rate_limits['example.com'] == 2.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_domain_extraction():
    """Test URL domain extraction"""
    client = RateLimitedHTTPClient()

    assert client._get_domain('https://api.flickr.com/services/rest/') == 'api.flickr.com'
    assert client._get_domain('http://example.com/path') == 'example.com'
    assert client._get_domain('invalid-url') == 'default'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_throttler_creation():
    """Test throttler creation per domain"""
    rate_limits = {'api.flickr.com': 1.0, 'api.imgur.com': 2.0}
    client = RateLimitedHTTPClient(rate_limits=rate_limits)

    # Test Flickr throttler
    flickr_throttler = await client._get_throttler('api.flickr.com')
    assert flickr_throttler.rate_limit == 1.0

    # Test Imgur throttler
    imgur_throttler = await client._get_throttler('api.imgur.com')
    assert imgur_throttler.rate_limit == 2.0

    # Test default throttler
    default_throttler = await client._get_throttler('unknown.com')
    assert default_throttler.rate_limit == 2.0  # Default rate


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting_timing():
    """Test that rate limiting actually enforces timing"""
    # Set very low rate limit for testing
    client = RateLimitedHTTPClient(rate_limits={'test.com': 2.0})  # 2 requests per second

    with patch.object(client, '_get_client') as mock_get_client:
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        mock_get_client.return_value = mock_http_client

        # Measure time for multiple requests
        start_time = time.time()

        # Make 3 requests - should take at least 1 second due to rate limiting
        await client.request('GET', 'https://test.com/1')
        await client.request('GET', 'https://test.com/2')
        await client.request('GET', 'https://test.com/3')

        elapsed = time.time() - start_time

        # Should take at least 1 second for 3 requests at 2 req/sec
        assert elapsed >= 0.8  # Allow some tolerance


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_mechanism():
    """Test retry mechanism with exponential backoff"""
    client = RateLimitedHTTPClient()

    with patch.object(client, '_get_client') as mock_get_client:
        mock_http_client = AsyncMock()

        # Simulate connection error then success
        import httpx
        mock_http_client.request.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed again"),
            AsyncMock(raise_for_status=MagicMock())  # Success on third try
        ]
        mock_get_client.return_value = mock_http_client

        # Should retry and eventually succeed
        response = await client.request('GET', 'https://example.com')
        assert response is not None

        # Should have made 3 calls (2 failures + 1 success)
        assert mock_http_client.request.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_exhaustion():
    """Test retry mechanism when all retries are exhausted"""
    client = RateLimitedHTTPClient()

    with patch.object(client, '_get_client') as mock_get_client:
        mock_http_client = AsyncMock()

        import httpx
        mock_http_client.request.side_effect = httpx.ConnectError("Persistent connection error")
        mock_get_client.return_value = mock_http_client

        # Should fail after retries are exhausted
        with pytest.raises(httpx.ConnectError):
            await client.request('GET', 'https://example.com')

        # Should have made 3 attempts (default retry count)
        assert mock_http_client.request.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_manager_singleton():
    """Test that HTTPClientManager is a singleton"""
    manager1 = await HTTPClientManager.get_instance()
    manager2 = await HTTPClientManager.get_instance()

    assert manager1 is manager2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_manager_named_clients():
    """Test named client creation and reuse"""
    manager = await HTTPClientManager.get_instance()

    # Get named client
    client1 = await manager.get_client('test_client', timeout=10.0)
    client2 = await manager.get_client('test_client', timeout=20.0)  # Different config

    # Should return the same instance (config from first call)
    assert client1 is client2
    assert client1.timeout == 10.0  # Original timeout preserved


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_http_client_function():
    """Test the convenience function for getting clients"""
    # Test default client
    default_client = await get_http_client()
    assert default_client is not None

    # Test named client
    named_client = await get_http_client('test', timeout=15.0)
    assert named_client is not None
    assert named_client.timeout == 15.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_cleanup():
    """Test client cleanup functionality"""
    client = RateLimitedHTTPClient()

    # Create a mock client
    with patch.object(client, '_get_client') as mock_get_client:
        mock_http_client = AsyncMock()
        mock_get_client.return_value = mock_http_client

        # Make a request to initialize client
        await client._get_client()

        # Close client
        await client.close()

        # Client should be None after close
        assert client._client is None
        assert len(client.throttlers) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager():
    """Test client context manager functionality"""
    async with RateLimitedHTTPClient() as client:
        assert client is not None

        with patch.object(client, 'close') as mock_close:
            pass  # Exit context

        # Close should be called
        mock_close.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test concurrent requests with rate limiting"""
    client = RateLimitedHTTPClient(rate_limits={'httpbin.org': 5.0})  # 5 req/sec

    with patch.object(client, '_get_client') as mock_get_client:
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        mock_get_client.return_value = mock_http_client

        # Make 10 concurrent requests
        start_time = time.time()
        tasks = [
            client.request('GET', f'https://httpbin.org/get?id={i}')
            for i in range(10)
        ]

        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # Should take at least 1.5 seconds for 10 requests at 5 req/sec
        assert elapsed >= 1.0  # Allow some tolerance for test environment