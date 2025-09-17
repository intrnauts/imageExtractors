import pytest
from image_extractor.utils.validation import (
    validate_url, validate_api_key, validate_rate_limit, validate_flickr_url,
    validate_extraction_options, validate_configuration_dict, sanitize_url,
    get_platform_from_url
)
from image_extractor.exceptions import ValidationError, InvalidURLError


@pytest.mark.unit
def test_validate_url_success():
    """Test successful URL validation"""
    valid_urls = [
        "https://www.flickr.com/photos/user/12345",
        "http://example.com/path",
        "https://api.imgur.com/3/image/abc123",
        "https://subdomain.example.org/resource"
    ]

    for url in valid_urls:
        assert validate_url(url) is True


@pytest.mark.unit
def test_validate_url_failures():
    """Test URL validation failures"""
    test_cases = [
        ("", "URL cannot be empty"),
        ("   ", "URL cannot be empty after trimming"),
        ("not-a-url", "URL must include a scheme"),
        ("ftp://example.com", "URL scheme must be one of"),
        ("https://", "URL must include a domain name"),
        ("https://invalid..domain", "Invalid domain name format"),
    ]

    for url, expected_error in test_cases:
        with pytest.raises(InvalidURLError) as exc_info:
            validate_url(url)
        assert expected_error in str(exc_info.value)


@pytest.mark.unit
def test_validate_url_custom_schemes():
    """Test URL validation with custom allowed schemes"""
    assert validate_url("ftp://example.com", allow_schemes=["ftp"]) is True

    with pytest.raises(InvalidURLError):
        validate_url("ftp://example.com", allow_schemes=["https"])


@pytest.mark.unit
def test_validate_api_key_success():
    """Test successful API key validation"""
    valid_keys = [
        "abc123def456",
        "very-long-api-key-with-special-chars_123",
        "0123456789abcdef"
    ]

    for key in valid_keys:
        assert validate_api_key(key, "test_platform") is True


@pytest.mark.unit
def test_validate_api_key_failures():
    """Test API key validation failures"""
    test_cases = [
        ("", "API key cannot be empty"),
        ("   ", "API key cannot be empty after trimming"),
        ("short", "API key must be at least 10 characters"),
        ("your_flickr_key", "API key appears to be a placeholder"),
        ("test_key_123", "API key appears to be a placeholder"),
        ("dummy_api_key", "API key appears to be a placeholder"),
    ]

    for key, expected_error in test_cases:
        with pytest.raises(ValidationError) as exc_info:
            validate_api_key(key, "test_platform")
        assert expected_error in str(exc_info.value)


@pytest.mark.unit
def test_validate_rate_limit_success():
    """Test successful rate limit validation"""
    valid_rates = [0.1, 1.0, 5.5, 50]

    for rate in valid_rates:
        assert validate_rate_limit(rate, "test_platform") is True


@pytest.mark.unit
def test_validate_rate_limit_failures():
    """Test rate limit validation failures"""
    test_cases = [
        ("not_a_number", "rate limit must be a number"),
        (0, "rate limit must be positive"),
        (-1.5, "rate limit must be positive"),
        (150, "rate limit seems too high"),
    ]

    for rate, expected_error in test_cases:
        with pytest.raises(ValidationError) as exc_info:
            validate_rate_limit(rate, "test_platform")
        assert expected_error in str(exc_info.value)


@pytest.mark.unit
def test_validate_flickr_url_success():
    """Test successful Flickr URL validation"""
    test_cases = [
        ("https://flickr.com/photos/user/12345678", "photo", "12345678"),
        ("https://www.flickr.com/p/abc123", "photo", "abc123"),
        ("https://flickr.com/photos/user/albums/123456", "photoset", "123456"),
        ("https://flickr.com/photos/user/sets/789012", "photoset", "789012"),
    ]

    for url, expected_type, expected_id in test_cases:
        result = validate_flickr_url(url)
        assert result['type'] == expected_type
        assert result['id'] == expected_id
        assert result['url'] == url


@pytest.mark.unit
def test_validate_flickr_url_failures():
    """Test Flickr URL validation failures"""
    invalid_urls = [
        "https://imgur.com/gallery/abc123",
        "https://flickr.com/groups/12345",
        "https://flickr.com/explore",
        "not-a-url"
    ]

    for url in invalid_urls:
        with pytest.raises(InvalidURLError):
            validate_flickr_url(url)


@pytest.mark.unit
def test_validate_extraction_options_success():
    """Test successful extraction options validation"""
    test_cases = [
        ({}, {}),
        ({"size": "large"}, {"size": "large"}),
        ({"format": "json"}, {"format": "json"}),
        ({"timeout": 60}, {"timeout": 60}),
        ({"max_images": 50}, {"max_images": 50}),
        ({"size": "medium", "format": "detailed", "timeout": 30},
         {"size": "medium", "format": "detailed", "timeout": 30}),
    ]

    for input_options, expected_output in test_cases:
        result = validate_extraction_options(input_options)
        assert result == expected_output


@pytest.mark.unit
def test_validate_extraction_options_failures():
    """Test extraction options validation failures"""
    test_cases = [
        ("not_a_dict", "Options must be a dictionary"),
        ({"size": "invalid"}, "Size must be one of"),
        ({"format": "invalid"}, "Format must be one of"),
        ({"timeout": 0}, "Timeout must be a positive number"),
        ({"timeout": 500}, "Timeout cannot exceed 300 seconds"),
        ({"max_images": 0}, "max_images must be a positive integer"),
        ({"max_images": 2000}, "max_images cannot exceed 1000"),
    ]

    for options, expected_error in test_cases:
        with pytest.raises(ValidationError) as exc_info:
            validate_extraction_options(options)
        assert expected_error in str(exc_info.value)


@pytest.mark.unit
def test_validate_configuration_dict():
    """Test configuration dictionary validation"""
    # Valid configuration
    valid_config = {
        "http": {
            "max_connections": 100,
            "timeout": 30.0
        },
        "rate_limits": {
            "flickr_api": 0.5,
            "imgur_api": 1.0
        },
        "extractors": {
            "batch_size": 5,
            "cache_ttl_seconds": 300
        },
        "api_keys": {
            "flickr": "valid_api_key_123456"
        }
    }

    errors = validate_configuration_dict(valid_config)
    assert len(errors) == 0

    # Invalid configuration
    invalid_config = {
        "http": {
            "max_connections": -1,
            "timeout": 0
        },
        "rate_limits": {
            "flickr_api": 0
        },
        "extractors": {
            "batch_size": 0,
            "cache_ttl_seconds": -1
        }
    }

    errors = validate_configuration_dict(invalid_config)
    assert len(errors) > 0
    assert any("max_connections must be positive" in error for error in errors)
    assert any("timeout must be positive" in error for error in errors)
    assert any("rate limit must be positive" in error for error in errors)


@pytest.mark.unit
def test_sanitize_url():
    """Test URL sanitization"""
    test_cases = [
        ("  https://example.com  ", "https://example.com"),
        ("https://example.com\x00\x01", "https://example.com"),
        ("https://example.com\t\n", "https://example.com"),
    ]

    for input_url, expected_output in test_cases:
        result = sanitize_url(input_url)
        assert result == expected_output

    # Test sanitization failure
    with pytest.raises(InvalidURLError):
        sanitize_url("")


@pytest.mark.unit
def test_get_platform_from_url():
    """Test platform detection from URLs"""
    test_cases = [
        ("https://flickr.com/photos/user/123", "flickr"),
        ("https://www.flickr.com/p/abc", "flickr"),
        ("https://imgur.com/gallery/abc", "imgur"),
        ("https://www.imgur.com/abc", "imgur"),
        ("https://instagram.com/p/abc", "instagram"),
        ("https://unknown.com/path", None),
        ("invalid-url", None),
    ]

    for url, expected_platform in test_cases:
        result = get_platform_from_url(url)
        assert result == expected_platform