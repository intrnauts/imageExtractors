"""
Configuration management for the image extractor package.
"""

import os
from typing import Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class HTTPConfig:
    """HTTP client configuration."""
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff_factor: float = 1.0


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for different platforms."""
    flickr_api: float = 0.5  # requests per second
    imgur_api: float = 1.0
    instagram_api: float = 0.5
    default: float = 2.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for HTTP client."""
        return {
            'api.flickr.com': self.flickr_api,
            'api.imgur.com': self.imgur_api,
            'graph.instagram.com': self.instagram_api,
        }


@dataclass
class ExtractorConfig:
    """Configuration for individual extractors."""
    batch_size: int = 5  # For photoset processing
    max_concurrent_requests: int = 10
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


@dataclass
class Config:
    """Main configuration class."""
    http: HTTPConfig = field(default_factory=HTTPConfig)
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)
    extractors: ExtractorConfig = field(default_factory=ExtractorConfig)

    # API Keys
    flickr_api_key: Optional[str] = None
    imgur_client_id: Optional[str] = None
    instagram_access_token: Optional[str] = None

    def __post_init__(self):
        """Load configuration from environment variables."""
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # API Keys
        self.flickr_api_key = os.getenv('FLICKR_API_KEY')
        self.imgur_client_id = os.getenv('IMGUR_CLIENT_ID')
        self.instagram_access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')

        # HTTP Configuration
        if os.getenv('HTTP_MAX_CONNECTIONS'):
            self.http.max_connections = int(os.getenv('HTTP_MAX_CONNECTIONS'))

        if os.getenv('HTTP_TIMEOUT'):
            self.http.timeout = float(os.getenv('HTTP_TIMEOUT'))

        if os.getenv('HTTP_MAX_RETRIES'):
            self.http.max_retries = int(os.getenv('HTTP_MAX_RETRIES'))

        # Rate Limits
        if os.getenv('RATE_LIMIT_FLICKR'):
            self.rate_limits.flickr_api = float(os.getenv('RATE_LIMIT_FLICKR'))

        if os.getenv('RATE_LIMIT_IMGUR'):
            self.rate_limits.imgur_api = float(os.getenv('RATE_LIMIT_IMGUR'))

        if os.getenv('RATE_LIMIT_INSTAGRAM'):
            self.rate_limits.instagram_api = float(os.getenv('RATE_LIMIT_INSTAGRAM'))

        # Extractor Configuration
        if os.getenv('EXTRACTOR_BATCH_SIZE'):
            self.extractors.batch_size = int(os.getenv('EXTRACTOR_BATCH_SIZE'))

        if os.getenv('EXTRACTOR_MAX_CONCURRENT'):
            self.extractors.max_concurrent_requests = int(os.getenv('EXTRACTOR_MAX_CONCURRENT'))

        if os.getenv('EXTRACTOR_ENABLE_CACHING'):
            self.extractors.enable_caching = os.getenv('EXTRACTOR_ENABLE_CACHING').lower() in ('true', '1', 'yes')

        if os.getenv('EXTRACTOR_CACHE_TTL'):
            self.extractors.cache_ttl_seconds = int(os.getenv('EXTRACTOR_CACHE_TTL'))

    def validate(self) -> None:
        """Validate configuration values."""
        errors = []

        # Validate HTTP config
        if self.http.max_connections <= 0:
            errors.append("HTTP max_connections must be positive")

        if self.http.timeout <= 0:
            errors.append("HTTP timeout must be positive")

        if self.http.max_retries < 0:
            errors.append("HTTP max_retries cannot be negative")

        # Validate rate limits
        if self.rate_limits.flickr_api <= 0:
            errors.append("Flickr API rate limit must be positive")

        if self.rate_limits.imgur_api <= 0:
            errors.append("Imgur API rate limit must be positive")

        if self.rate_limits.instagram_api <= 0:
            errors.append("Instagram API rate limit must be positive")

        # Validate extractor config
        if self.extractors.batch_size <= 0:
            errors.append("Extractor batch_size must be positive")

        if self.extractors.max_concurrent_requests <= 0:
            errors.append("Extractor max_concurrent_requests must be positive")

        if self.extractors.cache_ttl_seconds < 0:
            errors.append("Extractor cache_ttl_seconds cannot be negative")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    def get_api_key(self, platform: str) -> Optional[str]:
        """Get API key for a specific platform."""
        key_mapping = {
            'flickr': self.flickr_api_key,
            'imgur': self.imgur_client_id,
            'instagram': self.instagram_access_token,
        }
        return key_mapping.get(platform.lower())

    def is_platform_configured(self, platform: str) -> bool:
        """Check if a platform is properly configured."""
        api_key = self.get_api_key(platform)
        return api_key is not None and api_key.strip() != ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        config = cls()

        if 'http' in data:
            http_data = data['http']
            config.http = HTTPConfig(**http_data)

        if 'rate_limits' in data:
            rate_data = data['rate_limits']
            config.rate_limits = RateLimitConfig(**rate_data)

        if 'extractors' in data:
            extractor_data = data['extractors']
            config.extractors = ExtractorConfig(**extractor_data)

        # API keys
        if 'api_keys' in data:
            api_keys = data['api_keys']
            config.flickr_api_key = api_keys.get('flickr')
            config.imgur_client_id = api_keys.get('imgur')
            config.instagram_access_token = api_keys.get('instagram')

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'http': {
                'max_connections': self.http.max_connections,
                'max_keepalive_connections': self.http.max_keepalive_connections,
                'keepalive_expiry': self.http.keepalive_expiry,
                'timeout': self.http.timeout,
                'max_retries': self.http.max_retries,
                'retry_backoff_factor': self.http.retry_backoff_factor,
            },
            'rate_limits': {
                'flickr_api': self.rate_limits.flickr_api,
                'imgur_api': self.rate_limits.imgur_api,
                'instagram_api': self.rate_limits.instagram_api,
                'default': self.rate_limits.default,
            },
            'extractors': {
                'batch_size': self.extractors.batch_size,
                'max_concurrent_requests': self.extractors.max_concurrent_requests,
                'enable_caching': self.extractors.enable_caching,
                'cache_ttl_seconds': self.extractors.cache_ttl_seconds,
            },
            'api_keys': {
                'flickr': self.flickr_api_key,
                'imgur': self.imgur_client_id,
                'instagram': self.instagram_access_token,
            }
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
        _config.validate()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    config.validate()
    _config = config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None