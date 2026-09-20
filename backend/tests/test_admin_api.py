import pytest
import uuid
from httpx import AsyncClient
from app.models.scheme import Scheme
from app.models.user import User

async def _get_auth_headers(client: AsyncClient, email: str, role: str = "user") -> dict:
    signup_payload = {
        "name": f"{role.capitalize()} User",
        "email": email,
        "password": "Password123!",
        "role": role,
        "consent": True
    }
    await client.post("/auth/signup", json=signup_payload)
    login_res = await client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_admin_access_control(client: AsyncClient, db_session):
    # 1. Regular user token -> 403 Forbidden
    user_headers = await _get_auth_headers(client, "regular_access@example.com", role="user")
    res_user = await client.get("/admin/schemes", headers=user_headers)
    assert res_user.status_code == 403

    # 2. Admin user token -> 200 OK
    admin_headers = await _get_auth_headers(client, "admin_access@example.com", role="admin")
    res_admin = await client.get("/admin/schemes", headers=admin_headers)
    assert res_admin.status_code == 200

@pytest.mark.asyncio
async def test_admin_verify_and_outdated_workflow(client: AsyncClient, db_session):
    # Seed an unverified scheme
    s = Scheme(
        id=uuid.uuid4(),
        name="Test Unverified Scheme",
        description="Scheme needing review",
        state="Maharashtra",
        status="unverified",
        source_url="https://maharashtra.gov.in/test-scheme"
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    admin_headers = await _get_auth_headers(client, "admin_verify@example.com", role="admin")

    # Verify scheme
    verify_res = await client.post(f"/admin/schemes/{s.id}/verify", headers=admin_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "active"

    # Mark outdated scheme
    outdated_res = await client.post(f"/admin/schemes/{s.id}/mark-outdated", headers=admin_headers)
    assert outdated_res.status_code == 200
    assert outdated_res.json()["status"] == "expired"
