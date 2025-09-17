"""
Custom exceptions for the image extractor package.

This module provides specific exception types for better error handling
and more informative error messages.
"""

from typing import Optional, Dict, Any


class ImageExtractorError(Exception):
    """Base exception for all image extractor errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class ConfigurationError(ImageExtractorError):
    """Raised when there's a configuration issue."""
    pass


class PlatformNotConfiguredError(ConfigurationError):
    """Raised when a platform is not properly configured."""

    def __init__(self, platform: str, missing_config: str):
        message = f"Platform '{platform}' is not configured: missing {missing_config}"
        details = {"platform": platform, "missing_config": missing_config}
        super().__init__(message, details)


class InvalidURLError(ImageExtractorError):
    """Raised when an invalid URL is provided."""

    def __init__(self, url: str, reason: str = "Invalid URL format"):
        message = f"Invalid URL: {reason}"
        details = {"url": url, "reason": reason}
        super().__init__(message, details)


class UnsupportedPlatformError(ImageExtractorError):
    """Raised when a URL is from an unsupported platform."""

    def __init__(self, url: str, supported_platforms: Optional[list] = None):
        message = f"Unsupported platform for URL"
        details = {"url": url}
        if supported_platforms:
            message += f". Supported platforms: {', '.join(supported_platforms)}"
            details["supported_platforms"] = supported_platforms
        super().__init__(message, details)


class ExtractionError(ImageExtractorError):
    """Raised when image extraction fails."""

    def __init__(self, url: str, platform: str, reason: str):
        message = f"Failed to extract images from {platform}"
        details = {"url": url, "platform": platform, "reason": reason}
        super().__init__(message, details)


class APIError(ExtractionError):
    """Raised when an external API returns an error."""

    def __init__(self, url: str, platform: str, api_response: Dict[str, Any], status_code: Optional[int] = None):
        reason = f"API error: {api_response.get('message', 'Unknown error')}"
        super().__init__(url, platform, reason)
        self.api_response = api_response
        self.status_code = status_code
        self.details.update({
            "api_response": api_response,
            "status_code": status_code
        })


class RateLimitExceededError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, url: str, platform: str, retry_after: Optional[int] = None):
        api_response = {"message": "Rate limit exceeded"}
        if retry_after:
            api_response["retry_after"] = retry_after
        super().__init__(url, platform, api_response, 429)
        self.retry_after = retry_after


class NetworkError(ImageExtractorError):
    """Raised when there's a network connectivity issue."""

    def __init__(self, url: str, reason: str, retry_count: int = 0):
        message = f"Network error accessing {url}: {reason}"
        details = {"url": url, "reason": reason, "retry_count": retry_count}
        super().__init__(message, details)


class TimeoutError(NetworkError):
    """Raised when a request times out."""

    def __init__(self, url: str, timeout_seconds: float, retry_count: int = 0):
        reason = f"Request timed out after {timeout_seconds} seconds"
        super().__init__(url, reason, retry_count)
        self.timeout_seconds = timeout_seconds


class ValidationError(ImageExtractorError):
    """Raised when input validation fails."""

    def __init__(self, field: str, value: Any, reason: str):
        message = f"Validation failed for field '{field}': {reason}"
        details = {"field": field, "value": value, "reason": reason}
        super().__init__(message, details)


class ExtractorInitializationError(ConfigurationError):
    """Raised when an extractor fails to initialize."""

    def __init__(self, extractor_class: str, reason: str):
        message = f"Failed to initialize {extractor_class}: {reason}"
        details = {"extractor_class": extractor_class, "reason": reason}
        super().__init__(message, details)


class ImageProcessingError(ImageExtractorError):
    """Raised when image processing fails."""

    def __init__(self, image_url: str, reason: str):
        message = f"Failed to process image: {reason}"
        details = {"image_url": image_url, "reason": reason}
        super().__init__(message, details)


def wrap_http_error(error: Exception, url: str, context: str = "") -> ImageExtractorError:
    """
    Convert HTTP errors to more specific ImageExtractorError types.

    Args:
        error: The original HTTP error
        url: The URL that caused the error
        context: Additional context about the operation

    Returns:
        An appropriate ImageExtractorError subclass
    """
    import httpx

    if isinstance(error, httpx.ConnectError):
        return NetworkError(url, f"Connection failed: {str(error)}")

    elif isinstance(error, httpx.TimeoutException):
        return TimeoutError(url, 30.0)  # Default timeout

    elif isinstance(error, httpx.HTTPStatusError):
        if error.response.status_code == 429:
            retry_after = error.response.headers.get("Retry-After")
            retry_after_int = int(retry_after) if retry_after and retry_after.isdigit() else None
            return RateLimitExceededError(url, "unknown", retry_after_int)

        elif 400 <= error.response.status_code < 500:
            reason = f"Client error {error.response.status_code}: {error.response.text}"
            return APIError(url, "unknown", {"message": reason}, error.response.status_code)

        elif 500 <= error.response.status_code < 600:
            reason = f"Server error {error.response.status_code}: {error.response.text}"
            return APIError(url, "unknown", {"message": reason}, error.response.status_code)

    # Default fallback
    return ImageExtractorError(f"HTTP error in {context}: {str(error)}", {"url": url, "original_error": str(error)})


def create_user_friendly_error(error: Exception, url: Optional[str] = None) -> str:
    """
    Create a user-friendly error message from any exception.

    Args:
        error: The exception to convert
        url: Optional URL context

    Returns:
        A user-friendly error message
    """
    if isinstance(error, PlatformNotConfiguredError):
        platform = error.details.get("platform", "unknown")
        missing = error.details.get("missing_config", "configuration")
        return f"❌ {platform.title()} is not configured. Please set {missing} in your environment variables."

    elif isinstance(error, UnsupportedPlatformError):
        supported = error.details.get("supported_platforms", [])
        if supported:
            return f"❌ Unsupported platform. Supported platforms: {', '.join(supported)}"
        return "❌ Unsupported platform. Please check the URL format."

    elif isinstance(error, InvalidURLError):
        return f"❌ Invalid URL: {error.details.get('reason', 'Please check the URL format')}"

    elif isinstance(error, RateLimitExceededError):
        retry_after = error.retry_after
        if retry_after:
            return f"⏳ Rate limit exceeded. Please try again in {retry_after} seconds."
        return "⏳ Rate limit exceeded. Please try again later."

    elif isinstance(error, TimeoutError):
        return f"⏱️ Request timed out after {error.timeout_seconds} seconds. Please try again."

    elif isinstance(error, NetworkError):
        return f"🌐 Network error: {error.details.get('reason', 'Please check your internet connection')}"

    elif isinstance(error, APIError):
        platform = error.details.get("platform", "API")
        return f"🔌 {platform.title()} API error: {error.details.get('reason', 'Service temporarily unavailable')}"

    elif isinstance(error, ConfigurationError):
        return f"⚙️ Configuration error: {error.message}"

    elif isinstance(error, ValidationError):
        field = error.details.get("field", "input")
        reason = error.details.get("reason", "invalid value")
        return f"📝 Invalid {field}: {reason}"

    elif isinstance(error, ImageExtractorError):
        return f"❌ {error.message}"

    else:
        # Generic error handling
        return f"❌ An unexpected error occurred: {str(error)}"