import pytest
from abc import ABC
from image_extractor.extractors.base import BaseExtractor


class ConcreteExtractor(BaseExtractor):
    """Concrete implementation for testing"""

    @property
    def platform_name(self) -> str:
        return "test"

    @property
    def url_patterns(self) -> list:
        return [
            r'test\.com/photos/\d+',
            r'test\.com/albums/.*',
            r'example\.test/.*'
        ]

    async def extract(self, url: str, options: dict) -> dict:
        return {"platform": "test", "url": url}


@pytest.mark.unit
def test_base_extractor_is_abstract():
    """Test that BaseExtractor cannot be instantiated directly"""
    with pytest.raises(TypeError):
        BaseExtractor()


@pytest.mark.unit
def test_concrete_extractor_properties():
    """Test concrete extractor properties"""
    extractor = ConcreteExtractor()

    assert extractor.platform_name == "test"
    assert isinstance(extractor.url_patterns, list)
    assert len(extractor.url_patterns) == 3


@pytest.mark.unit
def test_matches_url_positive():
    """Test URL matching for valid patterns"""
    extractor = ConcreteExtractor()

    # Test URLs that should match
    valid_urls = [
        "https://test.com/photos/12345",
        "http://test.com/photos/67890",
        "https://test.com/albums/my-album",
        "https://test.com/albums/",
        "https://example.test/anything",
        "http://example.test/path/to/resource"
    ]

    for url in valid_urls:
        assert extractor.matches_url(url), f"URL should match: {url}"


@pytest.mark.unit
def test_matches_url_negative():
    """Test URL matching for invalid patterns"""
    extractor = ConcreteExtractor()

    # Test URLs that should NOT match
    invalid_urls = [
        "https://other.com/photos/12345",
        "https://test.com/videos/12345",  # doesn't match photos pattern
        "https://test.com/photos/abc",     # photos should have digits only
        "https://nottest.com/albums/test",
        "https://example.com/test",        # should be example.test
        "not-a-url",
        ""
    ]

    for url in invalid_urls:
        assert not extractor.matches_url(url), f"URL should NOT match: {url}"


@pytest.mark.unit
def test_matches_url_case_insensitive():
    """Test that URL matching is case insensitive"""
    extractor = ConcreteExtractor()

    # Test case variations
    case_variants = [
        "https://TEST.COM/photos/12345",
        "https://Test.Com/PHOTOS/12345",
        "https://EXAMPLE.TEST/anything"
    ]

    for url in case_variants:
        assert extractor.matches_url(url), f"Case insensitive matching should work: {url}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_method():
    """Test the extract method implementation"""
    extractor = ConcreteExtractor()

    result = await extractor.extract("https://test.com/photos/12345", {})

    assert isinstance(result, dict)
    assert result["platform"] == "test"
    assert result["url"] == "https://test.com/photos/12345"


@pytest.mark.unit
def test_url_patterns_are_valid_regex():
    """Test that all URL patterns are valid regex"""
    import re

    extractor = ConcreteExtractor()

    for pattern in extractor.url_patterns:
        try:
            re.compile(pattern)
        except re.error:
            pytest.fail(f"Invalid regex pattern: {pattern}")


@pytest.mark.unit
def test_empty_url_patterns():
    """Test behavior with empty URL patterns"""

    class EmptyPatternsExtractor(BaseExtractor):
        @property
        def platform_name(self) -> str:
            return "empty"

        @property
        def url_patterns(self) -> list:
            return []

        async def extract(self, url: str, options: dict) -> dict:
            return {}

    extractor = EmptyPatternsExtractor()

    # Should not match any URL
    assert not extractor.matches_url("https://any.com/url")
    assert not extractor.matches_url("")


@pytest.mark.unit
def test_malformed_regex_patterns():
    """Test behavior with malformed regex patterns"""

    class BadPatternsExtractor(BaseExtractor):
        @property
        def platform_name(self) -> str:
            return "bad"

        @property
        def url_patterns(self) -> list:
            return ["[unclosed-bracket", "valid\.pattern"]

        async def extract(self, url: str, options: dict) -> dict:
            return {}

    extractor = BadPatternsExtractor()

    # Should handle regex errors gracefully
    # The first pattern will fail, but the second should work
    assert not extractor.matches_url("https://test.com/unclosed")
    assert extractor.matches_url("https://valid.pattern/test")