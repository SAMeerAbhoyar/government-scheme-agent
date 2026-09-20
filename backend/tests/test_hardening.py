import pytest
import uuid
from unittest.mock import patch
from app.models.user import User, Profile
from app.models.activity import LLMCall
from app.core.security import create_access_token, get_password_hash
from app.core.crypto import encrypt_value, decrypt_value
from app.agents.query_planner import QueryPlannerAgent
from app.agents.explainer import RecommendationExplainerAgent
from app.services.matching import MatchResult

@pytest.fixture
async def auth_user(db_session, client):
    user = User(
        name="Hardening User",
        email="hardening@example.com",
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
async def test_security_headers(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert "X-Request-ID" in res.headers

@pytest.mark.asyncio
async def test_crypto_encryption_and_decryption():
    raw_val = "OBC"
    encrypted = encrypt_value(raw_val)
    assert encrypted != raw_val
    decrypted = decrypt_value(encrypted)
    assert decrypted == raw_val

@pytest.mark.asyncio
async def test_account_export_and_deletion(db_session, auth_user):
    client, headers, user = auth_user

    # 1. Export account data
    res_exp = await client.get("/account/export", headers=headers)
    assert res_exp.status_code == 200
    data = res_exp.json()
    assert data["user"]["email"] == "hardening@example.com"

    # 2. Delete account
    res_del = await client.delete("/account", headers=headers)
    assert res_del.status_code == 200

    # Verify user no longer exists
    from sqlalchemy import select
    res_user = await db_session.execute(select(User).where(User.id == user.id))
    assert res_user.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_llm_downtime_fallback_no_500():
    planner = QueryPlannerAgent(api_key="mock_invalid_key")
    with patch("google.generativeai.GenerativeModel.generate_content_async", side_effect=Exception("API Key expired/quota exceeded")):
        plan = await planner.plan_query("scholarship for maharashtra student")
        assert plan.intent == "scheme_search"
        assert plan.category == "Education"
        assert plan.state == "Maharashtra"

    explainer = RecommendationExplainerAgent(api_key="mock_invalid_key")
    dummy_match = MatchResult(
        scheme_id=str(uuid.uuid4()),
        scheme_name="Scholarship Scheme",
        status="potentially_relevant",
        match_score=0.95
    )
    with patch("google.generativeai.GenerativeModel.generate_content_async", side_effect=Exception("API Error")):
        explanation = await explainer.explain_match(match_result=dummy_match, profile_data={})
        assert "Why am I seeing this?" in explanation
        assert "Final eligibility is determined" in explanation
