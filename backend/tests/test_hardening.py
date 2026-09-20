import pytest
import uuid
from unittest.mock import patch
from cryptography.fernet import Fernet, InvalidToken
from app.models.user import User, Profile
from app.models.scheme import Scheme
from app.models.activity import LLMCall
from app.core.config import Settings
from app.core.security import create_access_token, get_password_hash
from app.core.crypto import encrypt_value, decrypt_value, get_fernet_key
from app.services.notification_service import profile_to_dict
from app.services.matching import match_scheme_against_profile, MatchResult
from app.agents.query_planner import QueryPlannerAgent
from app.agents.explainer import RecommendationExplainerAgent

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
async def test_crypto_round_trip_encryption():
    raw_val = "OBC"
    key_correct = "my-secret-key-1234567890123456789032chars"
    encrypted = encrypt_value(raw_val, key=key_correct)
    assert encrypted != raw_val
    assert str(encrypted).startswith("gAAAA")

    decrypted = decrypt_value(encrypted, key=key_correct)
    assert decrypted == raw_val

@pytest.mark.asyncio
async def test_crypto_wrong_key_raises():
    raw_val = "120000.0"
    key_correct = "correct-key-1234567890123456789032chars"
    key_wrong = "wrong-key-999999999999999999999932chars"

    encrypted = encrypt_value(raw_val, key=key_correct)
    assert encrypted.startswith("gAAAA")

    with pytest.raises(ValueError, match="Failed to decrypt value"):
        decrypt_value(encrypted, key=key_wrong)

@pytest.mark.asyncio
async def test_crypto_plaintext_legacy_passes_through():
    legacy_val = "OBC"
    key = "some-encryption-key-min-32-characters"
    result = decrypt_value(legacy_val, key=key)
    assert result == "OBC"

@pytest.mark.asyncio
async def test_missing_or_short_key_fails_startup(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("PROFILE_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    valid_key = "a3xR9Z5u1v8w2y4z7A6B8C0D2E4F6G8H" # 32 chars
    short_key = "short"

    # Missing or short ENCRYPTION_KEY fails startup
    with pytest.raises(ValueError, match="ENCRYPTION_KEY is required"):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY=valid_key, ENCRYPTION_KEY="", _env_file=None)

    with pytest.raises(ValueError, match="ENCRYPTION_KEY is required"):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY=valid_key, ENCRYPTION_KEY=short_key, _env_file=None)

    # Missing or short JWT_SECRET_KEY fails startup
    with pytest.raises(ValueError, match="JWT_SECRET_KEY is required"):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="", ENCRYPTION_KEY=valid_key, _env_file=None)

    with pytest.raises(ValueError, match="JWT_SECRET_KEY is required"):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY=short_key, ENCRYPTION_KEY=valid_key, _env_file=None)



@pytest.mark.asyncio
async def test_encrypted_profile_matching_passes(db_session, auth_user):
    client, headers, user = auth_user

    # Create profile with sensitive encrypted columns
    profile = Profile(
        user_id=user.id,
        state="Maharashtra",
        age=22,
        gender="female",
        annual_income=100000.0,
        social_category="OBC",
        disability=False,
        bpl_card=True
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    # Verify decrypted values on ORM object
    assert profile.social_category == "OBC"
    assert profile.annual_income == 100000.0
    assert profile.bpl_card is True

    # Test scheme matching
    scheme = Scheme(
        name="Encrypted Profile Test Scheme",
        state="Maharashtra",
        status="active",
        eligibility_rules={
            "rules": [
                {"field": "state", "op": "eq", "value": "Maharashtra"},
                {"field": "social_category", "op": "eq", "value": "OBC"},
                {"field": "annual_income", "op": "lte", "value": 200000},
                {"field": "bpl_card", "op": "eq", "value": True}
            ]
        }
    )
    db_session.add(scheme)
    await db_session.commit()

    p_dict = profile_to_dict(profile)
    assert p_dict["social_category"] == "OBC"
    assert p_dict["annual_income"] == 100000.0
    assert p_dict["bpl_card"] is True

    match_res = match_scheme_against_profile(p_dict, scheme)
    assert match_res.status == "potentially_relevant"

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
