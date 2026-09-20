import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    payload = {
        "name": "Test Citizen",
        "email": "citizen@example.com",
        "password": "SecurePassword123!",
        "role": "user",
        "consent": True
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "citizen@example.com"
    assert data["name"] == "Test Citizen"
    assert data["role"] == "user"

@pytest.mark.asyncio
async def test_signup_without_consent(client: AsyncClient):
    payload = {
        "name": "No Consent Citizen",
        "email": "noconsent@example.com",
        "password": "SecurePassword123!",
        "role": "user",
        "consent": False
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert "consent" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    payload = {
        "name": "First User",
        "email": "duplicate@example.com",
        "password": "Password123!",
        "consent": True
    }
    res1 = await client.post("/auth/signup", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/auth/signup", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()

@pytest.mark.asyncio
async def test_login_and_me_flow(client: AsyncClient):
    # 1. Signup
    signup_payload = {
        "name": "Flow User",
        "email": "flow@example.com",
        "password": "ValidPassword123",
        "consent": True
    }
    await client.post("/auth/signup", json=signup_payload)

    # 2. Login
    login_payload = {
        "email": "flow@example.com",
        "password": "ValidPassword123"
    }
    login_res = await client.post("/auth/login", json=login_payload)
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    token = tokens["access_token"]

    # 3. Get /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "flow@example.com"

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    signup_payload = {
        "name": "User One",
        "email": "userone@example.com",
        "password": "CorrectPassword123",
        "consent": True
    }
    await client.post("/auth/signup", json=signup_payload)

    login_res = await client.post("/auth/login", json={"email": "userone@example.com", "password": "WrongPassword"})
    assert login_res.status_code == 401

@pytest.mark.asyncio
async def test_invalid_token_access(client: AsyncClient):
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 401
