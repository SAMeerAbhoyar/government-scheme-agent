import pytest
from unittest.mock import patch
from httpx import AsyncClient
from app.models.scheme import Scheme
from app.seed_demo import DEMO_SCHEMES

@pytest.fixture(autouse=True)
async def seed_test_schemes(db_session):
    for sdata in DEMO_SCHEMES:
        s = Scheme(**sdata)
        db_session.add(s)
    await db_session.commit()

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
    assert len(data["matches"]) == 30

@pytest.mark.asyncio
async def test_discover_query_endpoint(client: AsyncClient):
    headers = await _get_auth_headers(client, "disc_query@example.com")
    res = await client.post("/discover/query", json={"query": "scholarship for student in Maharashtra"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "query"
    assert "matches" in data

@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"query": ""},
    {"query": None},
    {},
    {"query": "", "category_filter": "Agriculture"},
    {"query": None, "category_filter": "Agriculture"}
])
async def test_discover_query_empty_text(client: AsyncClient, payload):
    headers = await _get_auth_headers(client, f"empty_text_{hash(str(payload))}@example.com")
    res = await client.post("/discover/query", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "query"
    assert "matches" in data
    assert len(data["matches"]) > 0

@pytest.mark.asyncio
@pytest.mark.parametrize("category_opt", [
    "Agriculture",
    "Girl child",
    "Women",
    "Scholarship and education",
    "Old age",
    "Poor and BPL support",
    "Health",
    "Housing",
    "Employment"
])
async def test_discover_query_every_category_option_returns_at_least_one(client: AsyncClient, category_opt):
    headers = await _get_auth_headers(client, f"cat_{category_opt.replace(' ', '_')}@example.com")
    res = await client.post("/discover/query", json={"category_filter": category_opt}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "query"
    matches = data.get("matches", [])
    assert len(matches) >= 1, f"Category {category_opt} returned 0 matches"

@pytest.mark.asyncio
@pytest.mark.parametrize("category_opt", [
    "All categories",
    "Agriculture",
    "Girl child",
    "Women",
    "Scholarship and education",
    "Old age",
    "Poor and BPL support",
    "Health",
    "Housing",
    "Employment"
])
async def test_blank_profile_every_category_option_returns_200_with_results(client: AsyncClient, category_opt):
    headers = await _get_auth_headers(client, f"blank_prof_{hash(category_opt)}@example.com")
    res = await client.post("/discover/query", json={"category_filter": category_opt}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "query"
    matches = data.get("matches", [])
    assert len(matches) >= 1

@pytest.mark.asyncio
async def test_discover_query_all_categories_returns_30(client: AsyncClient):
    headers = await _get_auth_headers(client, "all_cats@example.com")
    res = await client.post("/discover/query", json={"category_filter": "All categories"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "query"
    matches = data.get("matches", [])
    assert len(matches) == 30

@pytest.mark.asyncio
async def test_discover_query_fallback_with_llm_disabled(client: AsyncClient):
    headers = await _get_auth_headers(client, "llm_fallback@example.com")
    with patch("app.api.discovery.query_planner.plan_query", side_effect=RuntimeError("LLM Unavailable")):
        res = await client.post("/discover/query", json={"query": "farmer kisan"}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "query"
        matches = data.get("matches", [])
        assert len(matches) > 0
