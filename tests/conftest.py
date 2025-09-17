"""
Pytest configuration and shared fixtures for image extractor tests.
"""

import pytest
import os
from unittest.mock import patch
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables and paths"""
    # Ensure we're testing the local package
    project_root = Path(__file__).parent.parent
    os.environ['PYTHONPATH'] = str(project_root)

    # Set up test API key
    os.environ['FLICKR_API_KEY'] = 'test_api_key_for_testing'

    yield

    # Cleanup if needed
    pass


@pytest.fixture
def mock_flickr_api_key():
    """Provide a mock Flickr API key for tests"""
    with patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'}):
        yield 'test_key'


@pytest.fixture
def sample_flickr_responses():
    """Provide sample Flickr API responses for testing"""
    return {
        'photo_info': {
            'stat': 'ok',
            'photo': {
                'title': {'_content': 'Test Photo'},
                'description': {'_content': 'Test Description'},
                'owner': {'username': 'testuser'},
                'dates': {'taken': '2023-01-01 12:00:00'}
            }
        },
        'photo_sizes': {
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
        },
        'photoset_info': {
            'stat': 'ok',
            'photoset': {
                'title': {'_content': 'Test Album'},
                'description': {'_content': 'Test Album Description'}
            }
        },
        'photoset_photos': {
            'stat': 'ok',
            'photoset': {
                'photo': [
                    {'id': '1', 'title': 'Photo 1'},
                    {'id': '2', 'title': 'Photo 2'}
                ]
            }
        },
        'api_error': {
            'stat': 'fail',
            'code': 1,
            'message': 'Photo not found'
        }
    }


@pytest.fixture
def sample_urls():
    """Provide sample URLs for testing"""
    return {
        'flickr_photo': 'https://flickr.com/photos/user/12345678',
        'flickr_short': 'https://flickr.com/p/abc123',
        'flickr_album': 'https://flickr.com/photos/user/albums/123456',
        'flickr_set': 'https://flickr.com/photos/user/sets/123456',
        'invalid_url': 'https://unsupported.com/image/123',
        'malformed_url': 'not-a-url'
    }


@pytest.fixture
def expected_extraction_result():
    """Provide expected extraction result structure"""
    return {
        'platform': 'flickr',
        'type': 'single',
        'images': [
            {
                'url': 'https://live.staticflickr.com/test.jpg',
                'title': 'Test Photo',
                'description': 'Test Description',
                'width': 800,
                'height': 600,
                'size_label': 'Medium'
            }
        ],
        'metadata': {
            'photo_id': '12345678',
            'owner': 'testuser',
            'date_taken': '2023-01-01 12:00:00'
        }
    }