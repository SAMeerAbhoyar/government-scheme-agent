import pytest
import uuid
from app.models.scheme import Scheme
from app.services.matching import match_scheme_against_profile, rank_matches, MatchResult
from app.eligibility.schema import RuleGroup, RuleLeaf, OperatorEnum

def test_match_scheme_all_pass():
    rules = {
        "all_of": [
            {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": "Resident of MH"},
            {"field": "annual_income", "op": "<=", "value": 250000, "source_quote": "Income under 2.5L"}
        ]
    }
    scheme = Scheme(
        id=uuid.uuid4(),
        name="MH Test Scholarship",
        department="Social Welfare",
        category="Education",
        state="Maharashtra",
        status="active",
        eligibility_rules=rules
    )

    profile_data = {
        "state": "Maharashtra",
        "annual_income": 150000
    }

    res = match_scheme_against_profile(profile_data, scheme)
    assert res.status == "potentially_relevant"
    assert len(res.missing_fields) == 0

def test_match_scheme_required_fail():
    rules = {
        "all_of": [
            {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": "Resident of MH"},
            {"field": "annual_income", "op": "<=", "value": 250000, "source_quote": "Income under 2.5L"}
        ]
    }
    scheme = Scheme(
        id=uuid.uuid4(),
        name="MH Test Scholarship",
        state="Maharashtra",
        status="active",
        eligibility_rules=rules
    )

    profile_data = {
        "state": "Maharashtra",
        "annual_income": 500000 # Exceeds income limit
    }

    res = match_scheme_against_profile(profile_data, scheme)
    assert res.status == "not_matching"

def test_match_scheme_cannot_determine():
    rules = {
        "all_of": [
            {"field": "state", "op": "==", "value": "Maharashtra", "source_quote": "Resident of MH"},
            {"field": "annual_income", "op": "<=", "value": 250000, "source_quote": "Income under 2.5L"}
        ]
    }
    scheme = Scheme(
        id=uuid.uuid4(),
        name="MH Test Scholarship",
        state="Maharashtra",
        status="active",
        eligibility_rules=rules
    )

    profile_data = {
        "state": "Maharashtra"
        # annual_income is missing
    }

    res = match_scheme_against_profile(profile_data, scheme)
    assert res.status == "cannot_determine"
    assert "annual_income" in res.missing_fields

def test_rank_matches_priority():
    m1 = MatchResult(scheme_id="1", scheme_name="S1", status="not_matching")
    m2 = MatchResult(scheme_id="2", scheme_name="S2", status="cannot_determine", missing_fields=["a"])
    m3 = MatchResult(scheme_id="3", scheme_name="S3", status="potentially_relevant")
    m4 = MatchResult(scheme_id="4", scheme_name="S4", status="potentially_relevant", unverified=True)

    ranked = rank_matches([m1, m2, m3, m4])
    assert [m.scheme_id for m in ranked] == ["3", "4", "2", "1"]
