import pytest
import httpx
from unittest.mock import AsyncMock
from image_extractor.exceptions import (
    ImageExtractorError, ConfigurationError, PlatformNotConfiguredError,
    InvalidURLError, UnsupportedPlatformError, ExtractionError, APIError,
    RateLimitExceededError, NetworkError, TimeoutError, ValidationError,
    ExtractorInitializationError, ImageProcessingError, wrap_http_error,
    create_user_friendly_error
)


@pytest.mark.unit
def test_image_extractor_error_base():
    """Test base ImageExtractorError functionality"""
    # Basic error
    error = ImageExtractorError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.details == {}

    # Error with details
    details = {"key": "value", "number": 42}
    error_with_details = ImageExtractorError("Test error with details", details)
    assert error_with_details.details == details
    assert "key=value" in str(error_with_details)
    assert "number=42" in str(error_with_details)


@pytest.mark.unit
def test_platform_not_configured_error():
    """Test PlatformNotConfiguredError"""
    error = PlatformNotConfiguredError("flickr", "FLICKR_API_KEY")

    assert "flickr" in error.message
    assert "FLICKR_API_KEY" in error.message
    assert error.details["platform"] == "flickr"
    assert error.details["missing_config"] == "FLICKR_API_KEY"


@pytest.mark.unit
def test_invalid_url_error():
    """Test InvalidURLError"""
    url = "https://invalid-url"
    reason = "Invalid format"

    error = InvalidURLError(url, reason)

    assert reason in error.message
    assert error.details["url"] == url
    assert error.details["reason"] == reason


@pytest.mark.unit
def test_unsupported_platform_error():
    """Test UnsupportedPlatformError"""
    url = "https://unsupported.com/image/123"
    supported = ["flickr", "imgur"]

    # Without supported platforms list
    error1 = UnsupportedPlatformError(url)
    assert error1.details["url"] == url
    assert "supported_platforms" not in error1.details

    # With supported platforms list
    error2 = UnsupportedPlatformError(url, supported)
    assert error2.details["url"] == url
    assert error2.details["supported_platforms"] == supported
    assert "flickr" in error2.message
    assert "imgur" in error2.message


@pytest.mark.unit
def test_extraction_error():
    """Test ExtractionError"""
    url = "https://flickr.com/photos/user/123"
    platform = "flickr"
    reason = "API error"

    error = ExtractionError(url, platform, reason)

    assert platform in error.message
    assert error.details["url"] == url
    assert error.details["platform"] == platform
    assert error.details["reason"] == reason


@pytest.mark.unit
def test_api_error():
    """Test APIError"""
    url = "https://api.flickr.com/services/rest/"
    platform = "flickr"
    api_response = {"message": "Invalid API key", "code": 100}
    status_code = 401

    error = APIError(url, platform, api_response, status_code)

    assert "API error" in error.message
    assert error.api_response == api_response
    assert error.status_code == status_code
    assert error.details["api_response"] == api_response
    assert error.details["status_code"] == status_code


@pytest.mark.unit
def test_rate_limit_exceeded_error():
    """Test RateLimitExceededError"""
    url = "https://api.flickr.com/services/rest/"
    platform = "flickr"
    retry_after = 60

    error = RateLimitExceededError(url, platform, retry_after)

    assert "Rate limit exceeded" in error.message
    assert error.status_code == 429
    assert error.retry_after == retry_after
    assert error.api_response["retry_after"] == retry_after


@pytest.mark.unit
def test_network_error():
    """Test NetworkError"""
    url = "https://api.flickr.com/services/rest/"
    reason = "Connection refused"
    retry_count = 2

    error = NetworkError(url, reason, retry_count)

    assert "Network error" in error.message
    assert url in error.message
    assert error.details["url"] == url
    assert error.details["reason"] == reason
    assert error.details["retry_count"] == retry_count


@pytest.mark.unit
def test_timeout_error():
    """Test TimeoutError"""
    url = "https://api.flickr.com/services/rest/"
    timeout_seconds = 30.0

    error = TimeoutError(url, timeout_seconds)

    assert "timed out" in error.message
    assert str(timeout_seconds) in error.message
    assert error.timeout_seconds == timeout_seconds


@pytest.mark.unit
def test_validation_error():
    """Test ValidationError"""
    field = "api_key"
    value = "short"
    reason = "must be at least 10 characters"

    error = ValidationError(field, value, reason)

    assert field in error.message
    assert reason in error.message
    assert error.details["field"] == field
    assert error.details["value"] == value
    assert error.details["reason"] == reason


@pytest.mark.unit
def test_extractor_initialization_error():
    """Test ExtractorInitializationError"""
    extractor_class = "FlickrExtractor"
    reason = "Missing API key"

    error = ExtractorInitializationError(extractor_class, reason)

    assert extractor_class in error.message
    assert reason in error.message
    assert error.details["extractor_class"] == extractor_class
    assert error.details["reason"] == reason


@pytest.mark.unit
def test_image_processing_error():
    """Test ImageProcessingError"""
    image_url = "https://example.com/image.jpg"
    reason = "Invalid image format"

    error = ImageProcessingError(image_url, reason)

    assert "Failed to process image" in error.message
    assert reason in error.message
    assert error.details["image_url"] == image_url
    assert error.details["reason"] == reason


@pytest.mark.unit
def test_wrap_http_error_connect_error():
    """Test wrapping httpx.ConnectError"""
    url = "https://api.flickr.com/test"
    original_error = httpx.ConnectError("Connection failed")

    wrapped = wrap_http_error(original_error, url)

    assert isinstance(wrapped, NetworkError)
    assert url in wrapped.message
    assert "Connection failed" in wrapped.message


@pytest.mark.unit
def test_wrap_http_error_timeout():
    """Test wrapping httpx.TimeoutException"""
    url = "https://api.flickr.com/test"
    original_error = httpx.TimeoutException("Request timed out")

    wrapped = wrap_http_error(original_error, url)

    assert isinstance(wrapped, TimeoutError)
    assert url == wrapped.details["url"]


@pytest.mark.unit
def test_wrap_http_error_rate_limit():
    """Test wrapping 429 HTTP status error"""
    url = "https://api.flickr.com/test"

    # Mock response with rate limit
    mock_response = AsyncMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "60"}
    mock_response.text = "Rate limit exceeded"

    mock_request = AsyncMock()
    original_error = httpx.HTTPStatusError("Rate limit", request=mock_request, response=mock_response)

    wrapped = wrap_http_error(original_error, url)

    assert isinstance(wrapped, RateLimitExceededError)
    assert wrapped.retry_after == 60


@pytest.mark.unit
def test_wrap_http_error_client_error():
    """Test wrapping 4xx HTTP status error"""
    url = "https://api.flickr.com/test"

    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.text = "Not found"

    mock_request = AsyncMock()
    original_error = httpx.HTTPStatusError("Not found", request=mock_request, response=mock_response)

    wrapped = wrap_http_error(original_error, url)

    assert isinstance(wrapped, APIError)
    assert wrapped.status_code == 404
    assert "Not found" in wrapped.details["api_response"]["message"]


@pytest.mark.unit
def test_wrap_http_error_server_error():
    """Test wrapping 5xx HTTP status error"""
    url = "https://api.flickr.com/test"

    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"

    mock_request = AsyncMock()
    original_error = httpx.HTTPStatusError("Server error", request=mock_request, response=mock_response)

    wrapped = wrap_http_error(original_error, url)

    assert isinstance(wrapped, APIError)
    assert wrapped.status_code == 500


@pytest.mark.unit
def test_wrap_http_error_generic():
    """Test wrapping generic exception"""
    url = "https://api.flickr.com/test"
    original_error = ValueError("Some error")

    wrapped = wrap_http_error(original_error, url, "test context")

    assert isinstance(wrapped, ImageExtractorError)
    assert "test context" in wrapped.message
    assert url in wrapped.details["url"]


@pytest.mark.unit
def test_create_user_friendly_error_platform_not_configured():
    """Test user-friendly error for platform not configured"""
    error = PlatformNotConfiguredError("flickr", "FLICKR_API_KEY")
    message = create_user_friendly_error(error)

    assert "❌" in message
    assert "Flickr" in message
    assert "not configured" in message
    assert "FLICKR_API_KEY" in message


@pytest.mark.unit
def test_create_user_friendly_error_unsupported_platform():
    """Test user-friendly error for unsupported platform"""
    error = UnsupportedPlatformError("https://unsupported.com", ["flickr", "imgur"])
    message = create_user_friendly_error(error)

    assert "❌" in message
    assert "Unsupported platform" in message
    assert "flickr" in message
    assert "imgur" in message


@pytest.mark.unit
def test_create_user_friendly_error_invalid_url():
    """Test user-friendly error for invalid URL"""
    error = InvalidURLError("not-a-url", "Invalid format")
    message = create_user_friendly_error(error)

    assert "❌" in message
    assert "Invalid URL" in message
    assert "Invalid format" in message


@pytest.mark.unit
def test_create_user_friendly_error_rate_limit():
    """Test user-friendly error for rate limit"""
    error = RateLimitExceededError("https://api.test.com", "test", 60)
    message = create_user_friendly_error(error)

    assert "⏳" in message
    assert "Rate limit exceeded" in message
    assert "60 seconds" in message

    # Test without retry_after
    error_no_retry = RateLimitExceededError("https://api.test.com", "test")
    message_no_retry = create_user_friendly_error(error_no_retry)
    assert "try again later" in message_no_retry


@pytest.mark.unit
def test_create_user_friendly_error_timeout():
    """Test user-friendly error for timeout"""
    error = TimeoutError("https://api.test.com", 30.0)
    message = create_user_friendly_error(error)

    assert "⏱️" in message
    assert "timed out" in message
    assert "30.0 seconds" in message


@pytest.mark.unit
def test_create_user_friendly_error_network():
    """Test user-friendly error for network issues"""
    error = NetworkError("https://api.test.com", "Connection refused")
    message = create_user_friendly_error(error)

    assert "🌐" in message
    assert "Network error" in message


@pytest.mark.unit
def test_create_user_friendly_error_api():
    """Test user-friendly error for API issues"""
    error = APIError("https://api.test.com", "flickr", {"message": "Invalid key"})
    message = create_user_friendly_error(error)

    assert "🔌" in message
    assert "Flickr" in message
    assert "API error" in message


@pytest.mark.unit
def test_create_user_friendly_error_validation():
    """Test user-friendly error for validation"""
    error = ValidationError("api_key", "short", "too short")
    message = create_user_friendly_error(error)

    assert "📝" in message
    assert "Invalid api_key" in message
    assert "too short" in message


@pytest.mark.unit
def test_create_user_friendly_error_generic():
    """Test user-friendly error for generic exceptions"""
    error = ValueError("Some generic error")
    message = create_user_friendly_error(error)

    assert "❌" in message
    assert "unexpected error" in message
    assert "Some generic error" in message