"""
Basic setup tests to verify the test environment is working correctly.
"""

import pytest
import sys
from pathlib import Path


@pytest.mark.unit
def test_python_version():
    """Test that we're running on a supported Python version"""
    assert sys.version_info >= (3, 8), "Python 3.8+ required"


@pytest.mark.unit
def test_project_structure():
    """Test that the project structure is correct"""
    project_root = Path(__file__).parent.parent

    # Check main package exists
    assert (project_root / 'image_extractor').exists()
    assert (project_root / 'image_extractor' / '__init__.py').exists()

    # Check extractors module exists
    assert (project_root / 'image_extractor' / 'extractors').exists()
    assert (project_root / 'image_extractor' / 'extractors' / '__init__.py').exists()
    assert (project_root / 'image_extractor' / 'extractors' / 'base.py').exists()
    assert (project_root / 'image_extractor' / 'extractors' / 'flickr.py').exists()

    # Check main files exist
    assert (project_root / 'main.py').exists()
    assert (project_root / 'pyproject.toml').exists()


@pytest.mark.unit
def test_imports():
    """Test that all main modules can be imported"""
    # Test base imports
    from image_extractor.extractors.base import BaseExtractor
    from image_extractor.extractors import ExtractorRegistry
    from image_extractor.client import ImageExtractorClient

    # Test that classes are properly defined
    assert BaseExtractor is not None
    assert ExtractorRegistry is not None
    assert ImageExtractorClient is not None


@pytest.mark.unit
def test_test_fixtures(sample_urls, sample_flickr_responses, mock_flickr_api_key):
    """Test that pytest fixtures are working"""
    assert isinstance(sample_urls, dict)
    assert 'flickr_photo' in sample_urls

    assert isinstance(sample_flickr_responses, dict)
    assert 'photo_info' in sample_flickr_responses

    assert mock_flickr_api_key == 'test_key'


@pytest.mark.unit
def test_package_version():
    """Test that package version is accessible"""
    from image_extractor import __version__
    assert __version__ == "0.1.0"


@pytest.mark.unit
def test_dependencies_available():
    """Test that required dependencies are available"""
    try:
        import httpx
        import pydantic
        assert True
    except ImportError as e:
        pytest.fail(f"Required dependency not available: {e}")


@pytest.mark.unit
def test_environment_setup():
    """Test that test environment is properly configured"""
    import os

    # Check that test API key is set
    assert 'FLICKR_API_KEY' in os.environ
    assert os.environ['FLICKR_API_KEY'] == 'test_api_key_for_testing'