"""
Validation utilities for the image extractor package.

This module provides validation functions for URLs, configurations,
and other input data with detailed error messages.
"""

import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from ..exceptions import ValidationError, InvalidURLError, ConfigurationError


def validate_url(url: str, allow_schemes: Optional[List[str]] = None) -> bool:
    """
    Validate a URL format.

    Args:
        url: The URL to validate
        allow_schemes: Optional list of allowed schemes (default: ['http', 'https'])

    Returns:
        True if URL is valid

    Raises:
        InvalidURLError: If URL is invalid
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError(url, "URL cannot be empty or non-string")

    url = url.strip()
    if not url:
        raise InvalidURLError(url, "URL cannot be empty after trimming whitespace")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise InvalidURLError(url, f"Failed to parse URL: {str(e)}")

    # Check scheme
    allowed_schemes = allow_schemes or ['http', 'https']
    if not parsed.scheme:
        raise InvalidURLError(url, "URL must include a scheme (http:// or https://)")

    if parsed.scheme not in allowed_schemes:
        raise InvalidURLError(url, f"URL scheme must be one of: {', '.join(allowed_schemes)}")

    # Check netloc (domain)
    if not parsed.netloc:
        raise InvalidURLError(url, "URL must include a domain name")

    # Check for basic domain format
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if not re.match(domain_pattern, parsed.netloc):
        raise InvalidURLError(url, "Invalid domain name format")

    return True


def validate_api_key(api_key: str, platform: str, min_length: int = 10) -> bool:
    """
    Validate an API key format.

    Args:
        api_key: The API key to validate
        platform: The platform name for error messages
        min_length: Minimum required length

    Returns:
        True if API key is valid

    Raises:
        ValidationError: If API key is invalid
    """
    if not api_key or not isinstance(api_key, str):
        raise ValidationError("api_key", api_key, f"{platform} API key cannot be empty")

    api_key = api_key.strip()
    if not api_key:
        raise ValidationError("api_key", api_key, f"{platform} API key cannot be empty after trimming")

    if len(api_key) < min_length:
        raise ValidationError("api_key", api_key, f"{platform} API key must be at least {min_length} characters")

    # Check for placeholder values
    placeholder_patterns = [
        r'your_.*_key',
        r'replace_.*',
        r'insert_.*',
        r'add_.*_here',
        r'example_.*',
        r'test.*key',
        r'dummy.*',
        r'placeholder',
    ]

    for pattern in placeholder_patterns:
        if re.match(pattern, api_key, re.IGNORECASE):
            raise ValidationError("api_key", api_key, f"{platform} API key appears to be a placeholder value")

    return True


def validate_rate_limit(rate: float, platform: str) -> bool:
    """
    Validate a rate limit value.

    Args:
        rate: Rate limit in requests per second
        platform: Platform name for error messages

    Returns:
        True if rate limit is valid

    Raises:
        ValidationError: If rate limit is invalid
    """
    if not isinstance(rate, (int, float)):
        raise ValidationError("rate_limit", rate, f"{platform} rate limit must be a number")

    if rate <= 0:
        raise ValidationError("rate_limit", rate, f"{platform} rate limit must be positive")

    if rate > 100:
        raise ValidationError("rate_limit", rate, f"{platform} rate limit seems too high (>100 req/s)")

    return True


def validate_flickr_url(url: str) -> Dict[str, str]:
    """
    Validate and extract information from a Flickr URL.

    Args:
        url: The Flickr URL to validate

    Returns:
        Dictionary with extracted information (photo_id, photoset_id, etc.)

    Raises:
        InvalidURLError: If URL is not a valid Flickr URL
    """
    validate_url(url)

    patterns = {
        'photo': [
            r'flickr\.com/photos/[^/]+/(\d+)',
            r'flickr\.com/p/(\w+)',
        ],
        'photoset': [
            r'flickr\.com/photos/[^/]+/albums/(\d+)',
            r'flickr\.com/photos/[^/]+/sets/(\d+)',
        ]
    }

    for url_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return {
                    'type': url_type,
                    'id': match.group(1),
                    'url': url
                }

    raise InvalidURLError(url, "URL does not match any supported Flickr URL patterns")


def validate_extraction_options(options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extraction options.

    Args:
        options: Dictionary of extraction options

    Returns:
        Validated and sanitized options dictionary

    Raises:
        ValidationError: If options are invalid
    """
    if not isinstance(options, dict):
        raise ValidationError("options", options, "Options must be a dictionary")

    validated = {}

    # Validate size preference
    if 'size' in options:
        size = options['size']
        valid_sizes = ['thumbnail', 'small', 'medium', 'large', 'original']
        if size not in valid_sizes:
            raise ValidationError("size", size, f"Size must be one of: {', '.join(valid_sizes)}")
        validated['size'] = size

    # Validate format preference
    if 'format' in options:
        format_type = options['format']
        valid_formats = ['json', 'detailed']
        if format_type not in valid_formats:
            raise ValidationError("format", format_type, f"Format must be one of: {', '.join(valid_formats)}")
        validated['format'] = format_type

    # Validate timeout
    if 'timeout' in options:
        timeout = options['timeout']
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValidationError("timeout", timeout, "Timeout must be a positive number")
        if timeout > 300:  # 5 minutes max
            raise ValidationError("timeout", timeout, "Timeout cannot exceed 300 seconds")
        validated['timeout'] = timeout

    # Validate max_images
    if 'max_images' in options:
        max_images = options['max_images']
        if not isinstance(max_images, int) or max_images <= 0:
            raise ValidationError("max_images", max_images, "max_images must be a positive integer")
        if max_images > 1000:
            raise ValidationError("max_images", max_images, "max_images cannot exceed 1000")
        validated['max_images'] = max_images

    return validated


def validate_configuration_dict(config_dict: Dict[str, Any]) -> List[str]:
    """
    Validate a configuration dictionary and return list of errors.

    Args:
        config_dict: Configuration dictionary to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate HTTP configuration
    if 'http' in config_dict:
        http_config = config_dict['http']
        if not isinstance(http_config, dict):
            errors.append("HTTP configuration must be a dictionary")
        else:
            # Validate max_connections
            if 'max_connections' in http_config:
                max_conn = http_config['max_connections']
                if not isinstance(max_conn, int) or max_conn <= 0:
                    errors.append("HTTP max_connections must be a positive integer")
                elif max_conn > 1000:
                    errors.append("HTTP max_connections seems too high (>1000)")

            # Validate timeout
            if 'timeout' in http_config:
                timeout = http_config['timeout']
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    errors.append("HTTP timeout must be a positive number")
                elif timeout > 600:
                    errors.append("HTTP timeout seems too high (>600 seconds)")

    # Validate rate limits
    if 'rate_limits' in config_dict:
        rate_config = config_dict['rate_limits']
        if not isinstance(rate_config, dict):
            errors.append("Rate limits configuration must be a dictionary")
        else:
            for platform, rate in rate_config.items():
                try:
                    validate_rate_limit(rate, platform)
                except ValidationError as e:
                    errors.append(e.message)

    # Validate extractor configuration
    if 'extractors' in config_dict:
        ext_config = config_dict['extractors']
        if not isinstance(ext_config, dict):
            errors.append("Extractors configuration must be a dictionary")
        else:
            # Validate batch_size
            if 'batch_size' in ext_config:
                batch_size = ext_config['batch_size']
                if not isinstance(batch_size, int) or batch_size <= 0:
                    errors.append("Extractor batch_size must be a positive integer")
                elif batch_size > 50:
                    errors.append("Extractor batch_size seems too high (>50)")

            # Validate cache TTL
            if 'cache_ttl_seconds' in ext_config:
                ttl = ext_config['cache_ttl_seconds']
                if not isinstance(ttl, int) or ttl < 0:
                    errors.append("Extractor cache_ttl_seconds must be a non-negative integer")

    # Validate API keys
    if 'api_keys' in config_dict:
        api_keys = config_dict['api_keys']
        if not isinstance(api_keys, dict):
            errors.append("API keys configuration must be a dictionary")
        else:
            for platform, key in api_keys.items():
                if key:  # Only validate if key is provided
                    try:
                        validate_api_key(key, platform)
                    except ValidationError as e:
                        errors.append(e.message)

    return errors


def sanitize_url(url: str) -> str:
    """
    Sanitize a URL by removing unsafe characters and normalizing format.

    Args:
        url: The URL to sanitize

    Returns:
        Sanitized URL

    Raises:
        InvalidURLError: If URL cannot be sanitized
    """
    if not url:
        raise InvalidURLError(url, "Cannot sanitize empty URL")

    # Strip whitespace
    url = url.strip()

    # Remove any null bytes or control characters
    url = ''.join(char for char in url if ord(char) >= 32)

    # Validate the sanitized URL
    validate_url(url)

    return url


def get_platform_from_url(url: str) -> Optional[str]:
    """
    Determine the platform from a URL.

    Args:
        url: The URL to analyze

    Returns:
        Platform name or None if not recognized
    """
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc.lower()

        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]

        platform_mapping = {
            'flickr.com': 'flickr',
            'imgur.com': 'imgur',
            'instagram.com': 'instagram',
            'facebook.com': 'facebook',
            'pinterest.com': 'pinterest',
        }

        return platform_mapping.get(domain)

    except Exception:
        return None