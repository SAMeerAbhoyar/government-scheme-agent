import pytest
from app.agents.explainer import RecommendationExplainerAgent, verify_explanation_facts
from app.services.matching import MatchResult, RuleResultDetail

def test_verify_explanation_facts_valid():
    match_result = MatchResult(
        scheme_id="1",
        scheme_name="Scholarship Scheme 2026",
        status="potentially_relevant",
        rule_results=[
            RuleResultDetail(field="annual_income", op="<=", required_value=250000, user_value=150000, result="match")
        ]
    )

    explanation = "You match Scholarship Scheme 2026 because your annual income of 150000 is under 250000."
    is_valid = verify_explanation_facts(explanation, match_result)
    assert is_valid is True

def test_verify_explanation_facts_hallucination_reject():
    match_result = MatchResult(
        scheme_id="1",
        scheme_name="Scholarship Scheme 2026",
        status="potentially_relevant",
        rule_results=[
            RuleResultDetail(field="annual_income", op="<=", required_value=250000, user_value=150000, result="match")
        ]
    )

    # Hallucinated number 999999 not present in match result!
    hallucinated_explanation = "You get a bonus payout of 999999 INR per year!"
    is_valid = verify_explanation_facts(hallucinated_explanation, match_result)
    assert is_valid is False

@pytest.mark.asyncio
async def test_explainer_agent_fallback():
    agent = RecommendationExplainerAgent()
    match_result = MatchResult(
        scheme_id="1",
        scheme_name="PM Kisan Scheme",
        status="potentially_relevant",
        rule_results=[
            RuleResultDetail(field="land_holding_acres", op="<=", required_value=5.0, user_value=2.0, result="match")
        ]
    )

    profile_data = {"land_holding_acres": 2.0}
    explanation = await agent.explain(profile_data, match_result)
    assert "PM Kisan Scheme" in explanation
    assert "2.0" in explanation or "5.0" in explanation
