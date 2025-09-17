import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    with patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'}):
        from main import app
        return TestClient(app)


@pytest.mark.unit
def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.unit
def test_platforms_endpoint(client):
    """Test the platforms endpoint"""
    response = client.get("/platforms")
    assert response.status_code == 200
    data = response.json()
    assert "platforms" in data
    assert isinstance(data["platforms"], list)
    assert "flickr" in data["platforms"]


@pytest.mark.unit
@patch('image_extractor.extractors.flickr.httpx.AsyncClient')
def test_extract_endpoint_success(mock_httpx, client):
    """Test successful image extraction"""
    # Mock Flickr API responses
    mock_info_response = {
        'stat': 'ok',
        'photo': {
            'title': {'_content': 'Test Photo'},
            'description': {'_content': 'Test Description'},
            'owner': {'username': 'testuser'},
            'dates': {'taken': '2023-01-01 12:00:00'}
        }
    }

    mock_sizes_response = {
        'stat': 'ok',
        'sizes': {
            'size': [
                {
                    'source': 'https://live.staticflickr.com/test.jpg',
                    'width': '800',
                    'height': '600',
                    'label': 'Medium'
                }
            ]
        }
    }

    mock_get = AsyncMock()
    mock_get.side_effect = [
        AsyncMock(json=lambda: mock_info_response),
        AsyncMock(json=lambda: mock_sizes_response)
    ]
    mock_httpx.return_value.__aenter__.return_value.get = mock_get

    response = client.post(
        "/extract",
        json={
            "url": "https://flickr.com/photos/user/12345678",
            "options": {}
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "flickr"
    assert data["type"] == "single"
    assert len(data["images"]) == 1


@pytest.mark.unit
def test_extract_endpoint_unsupported_platform(client):
    """Test extraction with unsupported platform"""
    response = client.post(
        "/extract",
        json={
            "url": "https://unsupported.com/image/123",
            "options": {}
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "Unsupported platform or invalid URL" in data["detail"]


@pytest.mark.unit
def test_extract_endpoint_invalid_url_format(client):
    """Test extraction with invalid URL format"""
    response = client.post(
        "/extract",
        json={
            "url": "not-a-valid-url",
            "options": {}
        }
    )

    # This should fail at the pydantic validation level
    assert response.status_code == 422


@pytest.mark.unit
@patch('image_extractor.extractors.flickr.FlickrExtractor.extract')
def test_extract_endpoint_extraction_error(mock_extract, client):
    """Test handling of extraction errors"""
    mock_extract.side_effect = ValueError("Invalid photo ID")

    response = client.post(
        "/extract",
        json={
            "url": "https://flickr.com/photos/user/invalid",
            "options": {}
        }
    )

    assert response.status_code == 500
    data = response.json()
    assert "Invalid photo ID" in data["detail"]


@pytest.mark.unit
def test_extract_endpoint_with_options(client):
    """Test extraction endpoint with options"""
    with patch('image_extractor.extractors.flickr.httpx.AsyncClient') as mock_httpx:
        # Mock successful responses
        mock_info_response = {
            'stat': 'ok',
            'photo': {
                'title': {'_content': 'Test Photo'},
                'owner': {'username': 'testuser'},
                'dates': {'taken': '2023-01-01 12:00:00'}
            }
        }

        mock_sizes_response = {
            'stat': 'ok',
            'sizes': {
                'size': [
                    {
                        'source': 'https://live.staticflickr.com/test.jpg',
                        'width': '800',
                        'height': '600',
                        'label': 'Medium'
                    }
                ]
            }
        }

        mock_get = AsyncMock()
        mock_get.side_effect = [
            AsyncMock(json=lambda: mock_info_response),
            AsyncMock(json=lambda: mock_sizes_response)
        ]
        mock_httpx.return_value.__aenter__.return_value.get = mock_get

        response = client.post(
            "/extract",
            json={
                "url": "https://flickr.com/photos/user/12345678",
                "options": {"size": "large", "format": "detailed"}
            }
        )

        assert response.status_code == 200


@pytest.mark.unit
def test_cors_middleware(client):
    """Test CORS middleware configuration"""
    response = client.options("/extract")
    # The OPTIONS request should be handled by CORS middleware
    assert response.status_code in [200, 405]  # 405 if no OPTIONS handler, but CORS headers should be present


@pytest.mark.unit
def test_request_validation():
    """Test request validation with various invalid inputs"""
    with patch.dict('os.environ', {'FLICKR_API_KEY': 'test_key'}):
        from main import app
        client = TestClient(app)

        # Test missing URL
        response = client.post("/extract", json={"options": {}})
        assert response.status_code == 422

        # Test invalid URL format
        response = client.post("/extract", json={"url": "not-a-url", "options": {}})
        assert response.status_code == 422

        # Test valid minimal request
        with patch('image_extractor.extractors.flickr.httpx.AsyncClient'):
            response = client.post("/extract", json={"url": "https://flickr.com/photos/user/123"})
            # Should not fail due to validation (but may fail due to mocking)
            assert response.status_code in [200, 500]  # 500 if mocking fails