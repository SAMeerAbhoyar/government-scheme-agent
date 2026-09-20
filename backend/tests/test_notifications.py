import pytest
from datetime import datetime, timezone, timedelta
from app.models.user import User, Profile
from app.models.scheme import Scheme
from app.models.activity import SavedScheme, Notification
from app.core.security import create_access_token, get_password_hash
from app.services.notification_service import (
    notify_saved_scheme_changed,
    notify_approaching_deadlines,
    notify_new_relevant_scheme
)

@pytest.fixture
async def auth_setup(db_session, client):
    user = User(
        name="Notif User",
        email="notifuser@example.com",
        password_hash=get_password_hash("pass123"),
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers, user

@pytest.mark.asyncio
async def test_saved_scheme_changed_notification(db_session, auth_setup):
    client, headers, user = auth_setup
    scheme = Scheme(
        name="Saved Scheme Test",
        state="Maharashtra",
        status="active"
    )
    db_session.add(scheme)
    await db_session.commit()

    saved = SavedScheme(user_id=user.id, scheme_id=scheme.id)
    db_session.add(saved)
    await db_session.commit()

    # Trigger 1: scheme changed
    c1 = await notify_saved_scheme_changed(db_session, scheme.id)
    assert c1 == 1

    # Trigger 1 duplicate: should deduplicate (fire 0)
    c2 = await notify_saved_scheme_changed(db_session, scheme.id)
    assert c2 == 0

    # API check GET /notifications
    res = await client.get("/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["unread_count"] == 1
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["type"] == "scheme_change"
    notif_id = data["notifications"][0]["id"]

    # Mark as read
    res_read = await client.post(f"/notifications/{notif_id}/read", headers=headers)
    assert res_read.status_code == 200
    assert res_read.json()["read"] is True

@pytest.mark.asyncio
async def test_approaching_deadline_notification(db_session, auth_setup):
    client, headers, user = auth_setup
    deadline = datetime.now(timezone.utc) + timedelta(days=3)
    scheme = Scheme(
        name="Deadline Scheme Test",
        state="Central",
        status="active",
        deadline_date=deadline
    )
    db_session.add(scheme)
    await db_session.commit()

    saved = SavedScheme(user_id=user.id, scheme_id=scheme.id)
    db_session.add(saved)
    await db_session.commit()

    c1 = await notify_approaching_deadlines(db_session)
    assert c1 == 1

    # Duplicate trigger check
    c2 = await notify_approaching_deadlines(db_session)
    assert c2 == 0

@pytest.mark.asyncio
async def test_new_relevant_scheme_notification(db_session, auth_setup):
    client, headers, user = auth_setup

    # Create user profile
    profile = Profile(
        user_id=user.id,
        state="Maharashtra",
        age=22,
        gender="female",
        annual_income=100000.0
    )
    db_session.add(profile)
    await db_session.commit()

    # Create matching scheme
    scheme = Scheme(
        name="Women Student Support Scheme",
        state="Maharashtra",
        status="active",
        eligibility_rules={
            "rules": [
                {"field": "state", "op": "eq", "value": "Maharashtra"},
                {"field": "annual_income", "op": "lte", "value": 250000}
            ]
        }
    )
    db_session.add(scheme)
    await db_session.commit()

    # Trigger 3
    c1 = await notify_new_relevant_scheme(db_session, scheme.id)
    assert c1 == 1

    # Duplicate trigger check
    c2 = await notify_new_relevant_scheme(db_session, scheme.id)
    assert c2 == 0
