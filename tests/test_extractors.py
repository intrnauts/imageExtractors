import pytest
import httpx
import os
from unittest.mock import AsyncMock, patch, MagicMock
from image_extractor.extractors.flickr import FlickrExtractor
from image_extractor.extractors.base import BaseExtractor
from image_extractor.extractors import ExtractorRegistry

@pytest.mark.asyncio
async def test_flickr_extractor_matches_url():
    extractor = FlickrExtractor()

    # Test valid URLs
    assert extractor.matches_url("https://www.flickr.com/photos/user/12345678")
    assert extractor.matches_url("https://flickr.com/photos/user/12345678")
    assert extractor.matches_url("https://www.flickr.com/p/abc123")
    assert extractor.matches_url("https://flickr.com/photos/user/albums/123456")

    # Test invalid URLs
    assert not extractor.matches_url("https://imgur.com/gallery/abc123")
    assert not extractor.matches_url("https://example.com")

@pytest.mark.asyncio
async def test_flickr_extract_photo_id():
    extractor = FlickrExtractor()

    assert extractor._extract_photo_id("https://flickr.com/photos/user/12345678") == "12345678"
    assert extractor._extract_photo_id("https://flickr.com/p/abc123") == "abc123"
    assert extractor._extract_photo_id("https://example.com") is None

@pytest.mark.asyncio
async def test_flickr_extract_photoset_id():
    extractor = FlickrExtractor()

    assert extractor._extract_photoset_id("https://flickr.com/photos/user/albums/123456") == "123456"
    assert extractor._extract_photoset_id("https://flickr.com/photos/user/sets/123456") == "123456"
    assert extractor._extract_photoset_id("https://flickr.com/photos/user/12345678") is None

@pytest.mark.asyncio
@patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'})
async def test_flickr_single_photo_extraction():
    extractor = FlickrExtractor()

    # Mock API responses
    mock_info_response = {
        'stat': 'ok',
        'photo': {
            'title': {'_content': 'Test Photo'},
            'description': {'_content': 'Test Description'},
            'owner': {'username': 'testuser'},
            'dates': {'taken': '2023-01-01 12:00:00'}
        }
    }

    mock_sizes_response = {
        'stat': 'ok',
        'sizes': {
            'size': [
                {
                    'source': 'https://live.staticflickr.com/test_small.jpg',
                    'width': '240',
                    'height': '180',
                    'label': 'Small'
                },
                {
                    'source': 'https://live.staticflickr.com/test_large.jpg',
                    'width': '1024',
                    'height': '768',
                    'label': 'Large'
                }
            ]
        }
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_get = AsyncMock()
        mock_get.side_effect = [
            AsyncMock(json=lambda: mock_info_response),
            AsyncMock(json=lambda: mock_sizes_response)
        ]
        mock_client.return_value.__aenter__.return_value.get = mock_get

        result = await extractor.extract("https://flickr.com/photos/user/12345678", {})

        assert result['platform'] == 'flickr'
        assert result['type'] == 'single'
        assert len(result['images']) == 2
        assert result['images'][0]['title'] == 'Test Photo'
        assert result['metadata']['owner'] == 'testuser'

@pytest.mark.asyncio
async def test_flickr_no_api_key():
    with patch.dict('os.environ', {}, clear=True):
        extractor = FlickrExtractor()

        with pytest.raises(ValueError, match="Flickr API key not configured"):
            await extractor.extract("https://flickr.com/photos/user/12345678", {})


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'})
async def test_flickr_photoset_extraction():
    """Test photoset/album extraction"""
    extractor = FlickrExtractor()

    # Mock photoset info response
    mock_info_response = {
        'stat': 'ok',
        'photoset': {
            'title': {'_content': 'Test Album'},
            'description': {'_content': 'Test Album Description'}
        }
    }

    # Mock photos in set response
    mock_photos_response = {
        'stat': 'ok',
        'photoset': {
            'photo': [
                {'id': '1', 'title': 'Photo 1'},
                {'id': '2', 'title': 'Photo 2'}
            ]
        }
    }

    # Mock sizes responses for each photo
    mock_sizes_response = {
        'stat': 'ok',
        'sizes': {
            'size': [
                {
                    'source': 'https://live.staticflickr.com/test.jpg',
                    'width': '800',
                    'height': '600',
                    'label': 'Medium'
                }
            ]
        }
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_get = AsyncMock()
        # First call: photoset info, Second: photos in set, Third & Fourth: sizes for each photo
        mock_get.side_effect = [
            AsyncMock(json=lambda: mock_info_response),
            AsyncMock(json=lambda: mock_photos_response),
            AsyncMock(json=lambda: mock_sizes_response),
            AsyncMock(json=lambda: mock_sizes_response)
        ]
        mock_client.return_value.__aenter__.return_value.get = mock_get

        result = await extractor.extract("https://flickr.com/photos/user/albums/123456", {})

        assert result['platform'] == 'flickr'
        assert result['type'] == 'album'
        assert len(result['images']) == 2
        assert result['metadata']['title'] == 'Test Album'
        assert result['metadata']['photo_count'] == 2


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'})
async def test_flickr_api_error():
    """Test handling of Flickr API errors"""
    extractor = FlickrExtractor()

    # Mock API error response
    mock_error_response = {
        'stat': 'fail',
        'code': 1,
        'message': 'Photo not found'
    }

    with patch('httpx.AsyncClient') as mock_client:
        mock_get = AsyncMock()
        mock_get.side_effect = [
            AsyncMock(json=lambda: mock_error_response),
            AsyncMock(json=lambda: mock_error_response)
        ]
        mock_client.return_value.__aenter__.return_value.get = mock_get

        with pytest.raises(ValueError, match="Failed to fetch photo data from Flickr"):
            await extractor.extract("https://flickr.com/photos/user/12345678", {})


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'})
async def test_flickr_invalid_url():
    """Test handling of invalid Flickr URLs"""
    extractor = FlickrExtractor()

    with pytest.raises(ValueError, match="Could not extract Flickr ID from URL"):
        await extractor.extract("https://flickr.com/invalid/url", {})


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'})
async def test_flickr_http_error():
    """Test handling of HTTP errors during API calls"""
    extractor = FlickrExtractor()

    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
            "API Error", request=AsyncMock(), response=AsyncMock(status_code=500)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await extractor.extract("https://flickr.com/photos/user/12345678", {})


@pytest.mark.unit
def test_flickr_url_pattern_variations():
    """Test various Flickr URL patterns"""
    extractor = FlickrExtractor()

    # Test all supported URL patterns
    valid_patterns = [
        "https://flickr.com/photos/username/12345678",
        "https://www.flickr.com/photos/username/12345678",
        "http://flickr.com/photos/username/12345678",
        "https://flickr.com/p/abcdef",
        "https://flickr.com/photos/username/albums/123456",
        "https://flickr.com/photos/username/sets/123456"
    ]

    for url in valid_patterns:
        assert extractor.matches_url(url), f"Should match: {url}"

    # Test invalid patterns
    invalid_patterns = [
        "https://instagram.com/p/abcdef",
        "https://flickr.com/photos/",
        "https://flickr.com/groups/123456",
        "not-a-url"
    ]

    for url in invalid_patterns:
        assert not extractor.matches_url(url), f"Should NOT match: {url}"


@pytest.mark.unit
def test_flickr_id_extraction():
    """Test photo and photoset ID extraction"""
    extractor = FlickrExtractor()

    # Test photo ID extraction
    photo_tests = [
        ("https://flickr.com/photos/user/12345678", "12345678"),
        ("https://flickr.com/p/abcdef123", "abcdef123"),
        ("https://flickr.com/invalid/url", None)
    ]

    for url, expected in photo_tests:
        result = extractor._extract_photo_id(url)
        assert result == expected, f"Photo ID extraction failed for {url}"

    # Test photoset ID extraction
    set_tests = [
        ("https://flickr.com/photos/user/albums/123456", "123456"),
        ("https://flickr.com/photos/user/sets/789012", "789012"),
        ("https://flickr.com/photos/user/12345678", None)
    ]

    for url, expected in set_tests:
        result = extractor._extract_photoset_id(url)
        assert result == expected, f"Photoset ID extraction failed for {url}"