import pytest
import httpx
from unittest.mock import AsyncMock, patch
from extractors.flickr import FlickrExtractor

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