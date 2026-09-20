import pytest
from unittest.mock import patch, MagicMock
import httpx
from ui.api_client import APIClient, APIClientError

@pytest.fixture
def api_client():
    return APIClient(base_url="http://localhost:8000")

def test_api_client_login_success(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "token123", "token_type": "bearer"}

    with patch("httpx.post", return_value=mock_resp):
        res = api_client.login("user@example.com", "pass123")
        assert res["access_token"] == "token123"

def test_api_client_401_unauthorized(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401

    with patch("httpx.get", return_value=mock_resp):
        with pytest.raises(APIClientError) as exc_info:
            api_client.get_me("invalid_token")
        assert exc_info.value.status_code == 401
        assert "unauthorized" in exc_info.value.message.lower() or "expired" in exc_info.value.message.lower()

def test_api_client_422_validation_error(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 422
    mock_resp.json.return_value = {"detail": [{"loc": ["body", "email"], "msg": "invalid email format"}]}

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(APIClientError) as exc_info:
            api_client.login("invalid_email", "pass")
        assert exc_info.value.status_code == 422
        assert "invalid email format" in exc_info.value.message

def test_api_client_403_forbidden(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 403

    with patch("httpx.get", return_value=mock_resp):
        with pytest.raises(APIClientError) as exc_info:
            api_client.get_admin_overview("user_token")
        assert exc_info.value.status_code == 403
        assert "forbidden" in exc_info.value.message.lower() or "admin" in exc_info.value.message.lower()

def test_api_client_network_error(api_client):
    with patch("httpx.get", side_effect=httpx.RequestError("Connection refused")):
        with pytest.raises(APIClientError) as exc_info:
            api_client.get_profile("token")
        assert exc_info.value.status_code == 503
        assert "connect to backend" in exc_info.value.message.lower() or "connection error" in exc_info.value.message.lower()
