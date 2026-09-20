import pytest
import uuid
from httpx import AsyncClient

async def _get_auth_headers(client: AsyncClient, email: str) -> dict:
    signup_payload = {
        "name": "Test User",
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
async def test_compare_schemes_validation_error(client: AsyncClient):
    headers = await _get_auth_headers(client, "compare_user@example.com")
    # Compare with less than 2 schemes should fail with HTTP 400
    res = await client.post("/schemes/compare", json={"scheme_ids": [str(uuid.uuid4())]}, headers=headers)
    assert res.status_code == 400
    assert "between 2 and 4 schemes" in res.json()["detail"]

@pytest.mark.asyncio
async def test_history_endpoints(client: AsyncClient):
    headers = await _get_auth_headers(client, "history_user@example.com")
    res_search = await client.get("/history/search", headers=headers)
    assert res_search.status_code == 200
    assert isinstance(res_search.json(), list)

    res_rec = await client.get("/history/recommendations", headers=headers)
    assert res_rec.status_code == 200
    assert isinstance(res_rec.json(), list)
