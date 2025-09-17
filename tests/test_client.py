import pytest
import httpx
from unittest.mock import AsyncMock, patch
from image_extractor.client import ImageExtractorClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization with default and custom parameters"""
    # Default initialization
    client = ImageExtractorClient()
    assert client.base_url == "http://localhost:8000"
    assert client.timeout == 30.0

    # Custom initialization
    client = ImageExtractorClient(base_url="https://api.example.com", timeout=60.0)
    assert client.base_url == "https://api.example.com"
    assert client.timeout == 60.0

    # Test URL cleanup
    client = ImageExtractorClient(base_url="https://api.example.com/")
    assert client.base_url == "https://api.example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_images_success():
    """Test successful image extraction"""
    client = ImageExtractorClient()

    mock_response = {
        'platform': 'flickr',
        'type': 'single',
        'images': [
            {
                'url': 'https://example.com/image.jpg',
                'title': 'Test Image',
                'width': 800,
                'height': 600,
                'size_label': 'Medium'
            }
        ],
        'metadata': {'photo_id': '12345'}
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response_obj)

        result = await client.extract_images("https://flickr.com/photos/user/12345")

        assert result == mock_response
        assert result['platform'] == 'flickr'
        assert len(result['images']) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_images_connection_error():
    """Test handling of connection errors"""
    client = ImageExtractorClient()

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(httpx.ConnectError) as exc_info:
            await client.extract_images("https://flickr.com/photos/user/12345")

        assert "Failed to connect to image extractor service" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_images_timeout():
    """Test handling of timeout errors"""
    client = ImageExtractorClient()

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException) as exc_info:
            await client.extract_images("https://flickr.com/photos/user/12345")

        assert "Request timed out after 30.0s" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_images_http_error():
    """Test handling of HTTP status errors"""
    client = ImageExtractorClient()

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid URL"}
        mock_response.text = '{"detail": "Invalid URL"}'

        error = httpx.HTTPStatusError("Bad Request", request=AsyncMock(), response=mock_response)
        mock_client.return_value.__aenter__.return_value.post.side_effect = error

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.extract_images("https://invalid-url")

        assert "HTTP 400 error: Invalid URL" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_supported_platforms_success():
    """Test successful retrieval of supported platforms"""
    client = ImageExtractorClient()

    mock_response = {"platforms": ["flickr", "imgur"]}

    with patch('httpx.AsyncClient') as mock_client:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)

        result = await client.get_supported_platforms()

        assert result == ["flickr", "imgur"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_supported_platforms_error():
    """Test error handling in get_supported_platforms"""
    client = ImageExtractorClient()

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(httpx.ConnectError):
            await client.get_supported_platforms()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_images_with_options():
    """Test image extraction with options parameter"""
    client = ImageExtractorClient()

    options = {"size": "large", "format": "json"}

    with patch('httpx.AsyncClient') as mock_client:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = {"images": []}
        mock_response_obj.raise_for_status.return_value = None

        mock_post = AsyncMock(return_value=mock_response_obj)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        await client.extract_images("https://flickr.com/photos/user/12345", options)

        # Verify the options were passed in the request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['options'] == options