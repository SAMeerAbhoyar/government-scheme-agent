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

def test_api_client_422_validation_error_formatting(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 422
    mock_resp.json.return_value = {
        "detail": [
            {"loc": ["body", "category_filter"], "msg": "value is not a valid enumeration member"},
            {"loc": ["body", "query"], "msg": "field required"}
        ]
    }

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(APIClientError) as exc_info:
            api_client.discover_query("token", "scholarship", category_filter="InvalidCat")
        assert exc_info.value.status_code == 422
        assert "category_filter: value is not a valid enumeration member" in exc_info.value.message
        assert "query: field required" in exc_info.value.message
        assert "Validation Error: Validation Error" not in exc_info.value.message

def test_api_client_422_single_field_error(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 422
    mock_resp.json.return_value = {
        "detail": [{"loc": ["body", "email"], "msg": "invalid email format"}]
    }

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(APIClientError) as exc_info:
            api_client.login("invalid_email", "pass")
        assert exc_info.value.status_code == 422
        assert exc_info.value.message == "email: invalid email format"
        assert "Validation Error: Validation Error" not in exc_info.value.message

def test_discover_query_payload_matches_schema(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"mode": "query", "total_matches": 1, "matches": []}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        res = api_client.discover_query("token123", "scholarship for engineering", category_filter="Education")
        assert res["mode"] == "query"
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        json_payload = kwargs["json"]
        assert "query" in json_payload
        assert json_payload["query"] == "scholarship for engineering"
        assert json_payload["category_filter"] == "Education"
        assert "prompt" not in json_payload

def test_discover_profile_payload(api_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"mode": "profile", "total_matches": 0, "matches": []}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        res = api_client.discover_profile("token123")
        assert res["mode"] == "profile"
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        json_payload = kwargs["json"]
        assert json_payload == {}

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
