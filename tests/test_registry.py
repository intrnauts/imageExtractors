import pytest
from unittest.mock import MagicMock, patch
from image_extractor.extractors import ExtractorRegistry
from image_extractor.extractors.base import BaseExtractor


class MockExtractor(BaseExtractor):
    """Mock extractor for testing"""

    @property
    def platform_name(self) -> str:
        return "test_platform"

    @property
    def url_patterns(self) -> list:
        return [r'test\.com/.*']

    async def extract(self, url: str, options: dict) -> dict:
        return {"platform": "test_platform", "images": []}


@pytest.mark.unit
def test_registry_initialization():
    """Test registry initialization and extractor registration"""
    registry = ExtractorRegistry()

    # Should have at least the Flickr extractor
    assert len(registry.extractors) >= 1
    platform_names = registry.get_supported_platforms()
    assert "flickr" in platform_names


@pytest.mark.unit
def test_get_extractor_valid_url():
    """Test getting extractor for valid URLs"""
    registry = ExtractorRegistry()

    # Test Flickr URLs
    flickr_urls = [
        "https://flickr.com/photos/user/12345",
        "https://www.flickr.com/photos/user/12345",
        "https://flickr.com/p/abc123",
        "https://flickr.com/photos/user/albums/12345"
    ]

    for url in flickr_urls:
        extractor = registry.get_extractor(url)
        assert extractor is not None
        assert extractor.platform_name == "flickr"


@pytest.mark.unit
def test_get_extractor_invalid_url():
    """Test getting extractor for invalid URLs"""
    registry = ExtractorRegistry()

    invalid_urls = [
        "https://unsupported.com/image/123",
        "https://example.com",
        "not-a-url",
        ""
    ]

    for url in invalid_urls:
        extractor = registry.get_extractor(url)
        assert extractor is None


@pytest.mark.unit
def test_get_supported_platforms():
    """Test getting list of supported platforms"""
    registry = ExtractorRegistry()
    platforms = registry.get_supported_platforms()

    assert isinstance(platforms, list)
    assert len(platforms) > 0
    assert "flickr" in platforms


@pytest.mark.unit
def test_registry_with_custom_extractor():
    """Test registry with additional custom extractors"""
    with patch('image_extractor.extractors.FlickrExtractor') as mock_flickr:
        mock_flickr.return_value = MockExtractor()

        registry = ExtractorRegistry()

        # Test that custom extractor is registered
        extractor = registry.get_extractor("https://test.com/image/123")
        assert extractor is not None
        assert extractor.platform_name == "test_platform"


@pytest.mark.unit
def test_multiple_extractors_same_url():
    """Test behavior when multiple extractors might match a URL"""
    # Create registry with known state
    registry = ExtractorRegistry()

    # Flickr URLs should only match Flickr extractor
    extractor = registry.get_extractor("https://flickr.com/photos/user/12345")
    assert extractor is not None
    assert extractor.platform_name == "flickr"

    # Test that the first matching extractor is returned
    # (This tests the current implementation behavior)
    for url_pattern in extractor.url_patterns:
        if "flickr" in url_pattern:
            test_url = "https://flickr.com/photos/testuser/12345"
            found_extractor = registry.get_extractor(test_url)
            assert found_extractor.platform_name == "flickr"
            break