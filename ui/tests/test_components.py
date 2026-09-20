import pytest
from ui.components.cards import render_status_badge, render_rule_rows, render_scheme_card
from ui.components.tables import render_comparison_table
from ui.components.admin import render_admin_metrics, render_unverified_queue

def test_render_status_badge():
    b_relevant = render_status_badge("potentially_relevant")
    assert "Likely eligible" in b_relevant
    assert "#d1fae5" in b_relevant

    b_cannot = render_status_badge("cannot_determine")
    assert "Need more info" in b_cannot
    assert "#fef3c7" in b_cannot

    b_not = render_status_badge("not_matching")
    assert "Not eligible right now" in b_not
    assert "#f1f5f9" in b_not

    b_unverified = render_status_badge("potentially_relevant", unverified=True)
    assert "Unverified" in b_unverified

def test_render_rule_rows():
    rules = [
        {"field": "age", "op": "gte", "required_value": 18, "user_value": 22, "result": "match"},
        {"field": "social_category", "op": "eq", "required_value": "SC", "user_value": "General", "result": "no_match"},
        {"field": "annual_income", "op": "lte", "required_value": 200000, "user_value": None, "result": "unknown"}
    ]
    html = render_rule_rows(rules)
    assert "✓" in html
    assert "✕" in html
    assert "?" in html
    assert "Age" in html
    assert "Social Category" in html

def test_render_scheme_card():
    match = {
        "scheme_id": "12345678-1234-1234-1234-123456789012",
        "scheme_name": "Test Engineering Scholarship",
        "department": "Higher Education",
        "state": "Maharashtra",
        "category": "Education",
        "status": "potentially_relevant",
        "unverified": True,
        "explanation": "You meet all eligibility criteria.",
        "source_url": "https://example.gov.in/scheme",
        "application_url": "https://example.gov.in/apply",
        "rule_results": [
            {"field": "state", "op": "eq", "required_value": "Maharashtra", "user_value": "Maharashtra", "result": "match"}
        ]
    }
    card_html = render_scheme_card(match)
    assert "Test Engineering Scholarship" in card_html
    assert "Higher Education" in card_html
    assert "Likely eligible" in card_html
    assert "Unverified" in card_html
    assert "Official page" in card_html
    assert "Apply" in card_html
    assert "Why am I seeing this?" in card_html

def test_render_comparison_table():
    schemes = [
        {
            "name": "Scheme 1",
            "department": "Dept A",
            "state": "Maharashtra",
            "category": "Education",
            "benefits": "Rs 10,000",
            "application_url": "https://apply1.gov.in"
        },
        {
            "name": "Scheme 2",
            "department": "Dept B",
            "state": "Central",
            "category": "Agriculture",
            "benefits": "Rs 6,000",
            "application_url": "https://apply2.gov.in"
        }
    ]
    table_html = render_comparison_table(schemes)
    assert "Scheme 1" in table_html
    assert "Scheme 2" in table_html
    assert "Dept A" in table_html
    assert "Dept B" in table_html

def test_render_comparison_table_single_or_empty():
    empty_html = render_comparison_table([])
    assert "Select 2 to 4 schemes" in empty_html

    single_html = render_comparison_table([{"name": "Only One"}])
    assert "Please select at least 2 schemes" in single_html
