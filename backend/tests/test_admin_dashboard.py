import pytest
import uuid
from app.models.user import User
from app.models.scheme import Scheme
from app.core.security import create_access_token, get_password_hash

@pytest.fixture
async def user_client(db_session, client):
    user = User(
        name="Regular User",
        email="regular@example.com",
        password_hash=get_password_hash("pass123"),
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers

@pytest.fixture
async def admin_client(db_session, client):
    admin = User(
        name="Admin User",
        email="admin@example.com",
        password_hash=get_password_hash("admin123"),
        role="admin"
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    token = create_access_token(str(admin.id))
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers, admin

@pytest.mark.asyncio
async def test_non_admin_gets_403_on_all_admin_routes(user_client):
    client, headers = user_client
    dummy_id = str(uuid.uuid4())

    routes = [
        ("GET", "/admin/overview"),
        ("GET", "/admin/unverified"),
        ("GET", "/admin/schemes"),
        ("GET", f"/admin/schemes/{dummy_id}"),
        ("POST", f"/admin/schemes/{dummy_id}/verify"),
        ("POST", f"/admin/schemes/{dummy_id}/edit-rules"),
        ("POST", f"/admin/schemes/{dummy_id}/reject"),
        ("POST", f"/admin/schemes/{dummy_id}/mark-outdated"),
        ("GET", "/admin/changes"),
        ("GET", "/admin/source-health"),
        ("GET", "/admin/feedback"),
        ("POST", "/admin/ingest-now"),
    ]

    for method, path in routes:
        if method == "GET":
            res = await client.get(path, headers=headers)
        else:
            res = await client.post(path, json={}, headers=headers)
        assert res.status_code == 403, f"Expected 403 on {method} {path}, got {res.status_code}"

@pytest.mark.asyncio
async def test_admin_dashboard_flows(db_session, admin_client):
    client, headers, admin = admin_client

    # Create unverified scheme
    scheme = Scheme(
        name="Unverified Scheme Test",
        department="Education",
        category="Scholarship",
        state="Maharashtra",
        status="unverified",
        eligibility_rules={"rules": [{"field": "age", "op": "gte", "value": 18}]}
    )
    db_session.add(scheme)
    await db_session.commit()

    # 1. Overview
    res_overview = await client.get("/admin/overview", headers=headers)
    assert res_overview.status_code == 200
    data_overview = res_overview.json()
    assert "schemes_by_status" in data_overview
    assert data_overview["unverified_count"] == 1

    # 2. Unverified queue
    res_queue = await client.get("/admin/unverified", headers=headers)
    assert res_queue.status_code == 200
    assert len(res_queue.json()) == 1

    # 3. Edit rules
    res_edit = await client.post(
        f"/admin/schemes/{scheme.id}/edit-rules",
        json={"benefits": "Rs 10,000 per year"},
        headers=headers
    )
    assert res_edit.status_code == 200

    # 4. Verify scheme
    res_verify = await client.post(f"/admin/schemes/{scheme.id}/verify", headers=headers)
    assert res_verify.status_code == 200
    assert res_verify.json()["status"] == "active"

    # 5. Changes feed & source health & feedback
    res_changes = await client.get("/admin/changes", headers=headers)
    assert res_changes.status_code == 200

    res_health = await client.get("/admin/source-health", headers=headers)
    assert res_health.status_code == 200

    res_fb = await client.get("/admin/feedback", headers=headers)
    assert res_fb.status_code == 200
