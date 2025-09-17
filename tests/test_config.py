import pytest
import os
from unittest.mock import patch
from image_extractor.config import Config, HTTPConfig, RateLimitConfig, ExtractorConfig, get_config, set_config, reset_config


@pytest.mark.unit
def test_http_config_defaults():
    """Test HTTPConfig default values"""
    config = HTTPConfig()
    assert config.max_connections == 100
    assert config.max_keepalive_connections == 20
    assert config.keepalive_expiry == 30.0
    assert config.timeout == 30.0
    assert config.max_retries == 3
    assert config.retry_backoff_factor == 1.0


@pytest.mark.unit
def test_rate_limit_config_defaults():
    """Test RateLimitConfig default values"""
    config = RateLimitConfig()
    assert config.flickr_api == 0.5
    assert config.imgur_api == 1.0
    assert config.instagram_api == 0.5
    assert config.default == 2.0


@pytest.mark.unit
def test_rate_limit_config_to_dict():
    """Test RateLimitConfig to_dict conversion"""
    config = RateLimitConfig()
    rate_dict = config.to_dict()

    expected = {
        'api.flickr.com': 0.5,
        'api.imgur.com': 1.0,
        'graph.instagram.com': 0.5,
    }

    assert rate_dict == expected


@pytest.mark.unit
def test_extractor_config_defaults():
    """Test ExtractorConfig default values"""
    config = ExtractorConfig()
    assert config.batch_size == 5
    assert config.max_concurrent_requests == 10
    assert config.enable_caching is True
    assert config.cache_ttl_seconds == 300


@pytest.mark.unit
def test_config_defaults():
    """Test Config default values"""
    config = Config()
    assert isinstance(config.http, HTTPConfig)
    assert isinstance(config.rate_limits, RateLimitConfig)
    assert isinstance(config.extractors, ExtractorConfig)
    assert config.flickr_api_key is None
    assert config.imgur_client_id is None
    assert config.instagram_access_token is None


@pytest.mark.unit
def test_config_load_from_env():
    """Test loading configuration from environment variables"""
    env_vars = {
        'FLICKR_API_KEY': 'test_flickr_key',
        'IMGUR_CLIENT_ID': 'test_imgur_id',
        'INSTAGRAM_ACCESS_TOKEN': 'test_instagram_token',
        'HTTP_MAX_CONNECTIONS': '200',
        'HTTP_TIMEOUT': '60.0',
        'HTTP_MAX_RETRIES': '5',
        'RATE_LIMIT_FLICKR': '0.3',
        'RATE_LIMIT_IMGUR': '1.5',
        'RATE_LIMIT_INSTAGRAM': '0.8',
        'EXTRACTOR_BATCH_SIZE': '10',
        'EXTRACTOR_MAX_CONCURRENT': '20',
        'EXTRACTOR_ENABLE_CACHING': 'true',
        'EXTRACTOR_CACHE_TTL': '600',
    }

    with patch.dict(os.environ, env_vars):
        config = Config()

        # Check API keys
        assert config.flickr_api_key == 'test_flickr_key'
        assert config.imgur_client_id == 'test_imgur_id'
        assert config.instagram_access_token == 'test_instagram_token'

        # Check HTTP config
        assert config.http.max_connections == 200
        assert config.http.timeout == 60.0
        assert config.http.max_retries == 5

        # Check rate limits
        assert config.rate_limits.flickr_api == 0.3
        assert config.rate_limits.imgur_api == 1.5
        assert config.rate_limits.instagram_api == 0.8

        # Check extractor config
        assert config.extractors.batch_size == 10
        assert config.extractors.max_concurrent_requests == 20
        assert config.extractors.enable_caching is True
        assert config.extractors.cache_ttl_seconds == 600


@pytest.mark.unit
def test_config_validation_success():
    """Test successful configuration validation"""
    config = Config()
    # Should not raise any exception
    config.validate()


@pytest.mark.unit
def test_config_validation_failures():
    """Test configuration validation failures"""
    config = Config()

    # Test invalid HTTP config
    config.http.max_connections = -1
    with pytest.raises(ValueError, match="max_connections must be positive"):
        config.validate()

    config.http.max_connections = 100  # Reset
    config.http.timeout = 0
    with pytest.raises(ValueError, match="timeout must be positive"):
        config.validate()

    config.http.timeout = 30.0  # Reset
    config.http.max_retries = -1
    with pytest.raises(ValueError, match="max_retries cannot be negative"):
        config.validate()

    config.http.max_retries = 3  # Reset

    # Test invalid rate limits
    config.rate_limits.flickr_api = 0
    with pytest.raises(ValueError, match="Flickr API rate limit must be positive"):
        config.validate()

    config.rate_limits.flickr_api = 0.5  # Reset

    # Test invalid extractor config
    config.extractors.batch_size = 0
    with pytest.raises(ValueError, match="batch_size must be positive"):
        config.validate()

    config.extractors.batch_size = 5  # Reset
    config.extractors.cache_ttl_seconds = -1
    with pytest.raises(ValueError, match="cache_ttl_seconds cannot be negative"):
        config.validate()


@pytest.mark.unit
def test_get_api_key():
    """Test getting API keys for different platforms"""
    config = Config()
    config.flickr_api_key = 'flickr_key'
    config.imgur_client_id = 'imgur_key'
    config.instagram_access_token = 'instagram_key'

    assert config.get_api_key('flickr') == 'flickr_key'
    assert config.get_api_key('imgur') == 'imgur_key'
    assert config.get_api_key('instagram') == 'instagram_key'
    assert config.get_api_key('unknown') is None

    # Test case insensitive
    assert config.get_api_key('FLICKR') == 'flickr_key'


@pytest.mark.unit
def test_is_platform_configured():
    """Test platform configuration check"""
    config = Config()

    # No API keys configured
    assert not config.is_platform_configured('flickr')
    assert not config.is_platform_configured('imgur')

    # Configure Flickr
    config.flickr_api_key = 'test_key'
    assert config.is_platform_configured('flickr')
    assert not config.is_platform_configured('imgur')

    # Test empty string
    config.flickr_api_key = '   '
    assert not config.is_platform_configured('flickr')


@pytest.mark.unit
def test_config_from_dict():
    """Test creating configuration from dictionary"""
    config_data = {
        'http': {
            'max_connections': 150,
            'timeout': 45.0,
        },
        'rate_limits': {
            'flickr_api': 0.8,
            'imgur_api': 1.2,
        },
        'extractors': {
            'batch_size': 8,
            'enable_caching': False,
        },
        'api_keys': {
            'flickr': 'dict_flickr_key',
            'imgur': 'dict_imgur_key',
        }
    }

    config = Config.from_dict(config_data)

    assert config.http.max_connections == 150
    assert config.http.timeout == 45.0
    assert config.rate_limits.flickr_api == 0.8
    assert config.rate_limits.imgur_api == 1.2
    assert config.extractors.batch_size == 8
    assert config.extractors.enable_caching is False
    assert config.flickr_api_key == 'dict_flickr_key'
    assert config.imgur_client_id == 'dict_imgur_key'


@pytest.mark.unit
def test_config_to_dict():
    """Test converting configuration to dictionary"""
    config = Config()
    config.flickr_api_key = 'test_key'
    config.http.max_connections = 150

    config_dict = config.to_dict()

    assert config_dict['http']['max_connections'] == 150
    assert config_dict['api_keys']['flickr'] == 'test_key'
    assert 'rate_limits' in config_dict
    assert 'extractors' in config_dict


@pytest.mark.unit
def test_global_config_functions():
    """Test global configuration functions"""
    # Reset config first
    reset_config()

    # Get config (should create new one)
    config1 = get_config()
    assert config1 is not None

    # Get config again (should return same instance)
    config2 = get_config()
    assert config1 is config2

    # Set new config
    new_config = Config()
    new_config.flickr_api_key = 'test_key'
    set_config(new_config)

    # Should get the new config
    config3 = get_config()
    assert config3 is new_config
    assert config3.flickr_api_key == 'test_key'

    # Reset again
    reset_config()
    config4 = get_config()
    assert config4 is not config3  # Should be a new instance


@pytest.mark.unit
def test_config_validation_on_set():
    """Test that set_config validates the configuration"""
    invalid_config = Config()
    invalid_config.http.max_connections = -1

    with pytest.raises(ValueError):
        set_config(invalid_config)


@pytest.mark.unit
def test_env_var_caching_toggle():
    """Test caching toggle from environment variable"""
    test_cases = [
        ('true', True),
        ('false', False),
        ('1', True),
        ('0', False),
        ('yes', True),
        ('no', False),
        ('TRUE', True),
        ('FALSE', False),
    ]

    for env_value, expected in test_cases:
        with patch.dict(os.environ, {'EXTRACTOR_ENABLE_CACHING': env_value}):
            config = Config()
            assert config.extractors.enable_caching == expected