import pytest
from httpx import AsyncClient

async def _get_auth_headers(client: AsyncClient, email: str) -> dict:
    signup_payload = {
        "name": "Test Citizen",
        "email": email,
        "password": "Password123!",
        "role": "user",
        "consent": True
    }
    await client.post("/auth/signup", json=signup_payload)
    login_res = await client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_discover_profile_endpoint(client: AsyncClient):
    headers = await _get_auth_headers(client, "disc_prof@example.com")
    res = await client.post("/discover/profile", json={}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "profile"
    assert "matches" in data
    assert isinstance(data["matches"], list)

@pytest.mark.asyncio
async def test_discover_query_endpoint(client: AsyncClient):
    headers = await _get_auth_headers(client, "disc_query@example.com")
    res = await client.post("/discover/query", json={"query": "scholarship for student in Maharashtra"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "query"
    assert "query_plan" in data
    assert "matches" in data
