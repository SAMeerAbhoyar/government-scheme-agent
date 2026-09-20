import pytest
from httpx import AsyncClient

async def _get_auth_headers(client: AsyncClient, email: str = "profileuser@example.com") -> dict:
    signup_payload = {
        "name": "Profile User",
        "email": email,
        "password": "Password123!",
        "consent": True
    }
    await client.post("/auth/signup", json=signup_payload)

    login_res = await client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_get_and_update_profile(client: AsyncClient):
    headers = await _get_auth_headers(client, "profile1@example.com")

    # 1. GET profile (should be empty defaults)
    get_res = await client.get("/profile", headers=headers)
    assert get_res.status_code == 200
    p = get_res.json()
    assert p["age"] is None
    assert p["social_category"] is None

    # 2. PUT profile (update demographic fields)
    update_payload = {
        "age": 22,
        "gender": "Female",
        "state": "Maharashtra",
        "district": "Pune",
        "education_level": "Undergraduate",
        "course": "B.Tech Computer Science",
        "annual_income": 180000.00,
        "social_category": "OBC",
        "bpl_card": False
    }
    put_res = await client.put("/profile", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    updated_p = put_res.json()
    assert updated_p["age"] == 22
    assert updated_p["state"] == "Maharashtra"
    assert updated_p["annual_income"] == 180000.00
    assert updated_p["social_category"] == "OBC"

@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient):
    headers = await _get_auth_headers(client, "deleteuser@example.com")

    # Delete account
    del_res = await client.delete("/account", headers=headers)
    assert del_res.status_code == 200
    assert "deleted" in del_res.json()["message"].lower()

    # Subsequent request should fail with 401
    get_res = await client.get("/profile", headers=headers)
    assert get_res.status_code == 401
