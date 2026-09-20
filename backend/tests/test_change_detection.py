import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.models.scheme import Scheme, SchemeVersion, SchemeChange
from app.services.diff_service import compute_scheme_diff
from app.services.scheme_service import process_and_save_scheme
from app.services.maintenance import run_daily_maintenance, record_fetch_failure
from app.agents.extractor import SchemeExtractionOutput
from app.eligibility.schema import RuleGroup, RuleLeaf, OperatorEnum

def test_compute_scheme_diff_has_changes():
    old_data = {
        "name": "Scholarship A",
        "benefits": "1000 INR",
        "documents": ["Aadhaar"],
        "eligibility_rules": {
            "all_of": [{"field": "annual_income", "op": "<=", "value": 200000, "source_quote": "Income under 2L"}]
        }
    }

    new_data = {
        "name": "Scholarship A",
        "benefits": "2000 INR", # Changed
        "documents": ["Aadhaar", "Income Certificate"], # Added doc
        "eligibility_rules": {
            "all_of": [{"field": "annual_income", "op": "<=", "value": 300000, "source_quote": "Income under 3L"}] # Changed limit
        }
    }

    diff = compute_scheme_diff(old_data, new_data)
    assert diff["has_changes"] is True
    assert "benefits" in diff["changed_fields"]
    assert "documents" in diff["changed_fields"]
    assert "eligibility_rules" in diff["changed_fields"]
    assert diff["details"]["benefits"]["old"] == "1000 INR"
    assert diff["details"]["benefits"]["new"] == "2000 INR"

def test_compute_scheme_diff_no_changes():
    old_data = {
        "name": "Scholarship A",
        "benefits": "1000 INR",
        "documents": ["Aadhaar"],
        "eligibility_rules": {
            "all_of": [{"field": "annual_income", "op": "<=", "value": 200000, "source_quote": "Income under 2L"}]
        }
    }

    diff = compute_scheme_diff(old_data, old_data)
    assert diff["has_changes"] is False
    assert len(diff["changed_fields"]) == 0

@pytest.mark.asyncio
async def test_reingestion_creates_scheme_change(db_session):
    # Version 1
    raw_text_v1 = "Scholarship for student in Maharashtra. Income limit 200000 INR."
    url = "https://maharashtra.gov.in/scholarship-v1"
    
    rules_v1 = RuleGroup(all_of=[
        RuleLeaf(field="state", op=OperatorEnum.EQ, value="Maharashtra", source_quote="Resident of Maharashtra"),
        RuleLeaf(field="annual_income", op=OperatorEnum.LTE, value=200000, source_quote="Income limit 200000 INR")
    ])

    extracted_v1 = SchemeExtractionOutput(
        name="MH Student Scholarship",
        description="V1 description",
        department="Education",
        category="Education",
        state="Maharashtra",
        benefits="10000 INR per year",
        documents=["Aadhaar"],
        application_process="Apply online",
        application_url=url,
        eligibility_rules=rules_v1,
        extraction_confidence=0.95
    )

    s1, is_up1 = await process_and_save_scheme(
        db=db_session,
        extracted=extracted_v1,
        raw_text=raw_text_v1,
        source_url=url,
        content_hash="hash_v1"
    )

    # Version 2 with modified income limit
    raw_text_v2 = "Scholarship for student in Maharashtra. Income limit 300000 INR."
    rules_v2 = RuleGroup(all_of=[
        RuleLeaf(field="state", op=OperatorEnum.EQ, value="Maharashtra", source_quote="Resident of Maharashtra"),
        RuleLeaf(field="annual_income", op=OperatorEnum.LTE, value=300000, source_quote="Income limit 300000 INR")
    ])

    extracted_v2 = SchemeExtractionOutput(
        name="MH Student Scholarship",
        description="V2 description",
        department="Education",
        category="Education",
        state="Maharashtra",
        benefits="15000 INR per year", # Changed benefit
        documents=["Aadhaar", "Income Cert"],
        application_process="Apply online",
        application_url=url,
        eligibility_rules=rules_v2,
        extraction_confidence=0.95
    )

    s2, is_up2 = await process_and_save_scheme(
        db=db_session,
        extracted=extracted_v2,
        raw_text=raw_text_v2,
        source_url=url,
        content_hash="hash_v2"
    )

    # Verify SchemeChange row was created in DB
    changes_res = await db_session.execute(select(SchemeChange).where(SchemeChange.scheme_id == s1.id))
    changes = changes_res.scalars().all()
    assert len(changes) == 1
    assert changes[0].from_version == "hash_v1"
    assert changes[0].to_version == "hash_v2"
    assert changes[0].diff["has_changes"] is True

@pytest.mark.asyncio
async def test_maintenance_expiration_and_failures(db_session):
    past_date = datetime.now(timezone.utc) - timedelta(days=2)
    s_expired = Scheme(
        name="Expired Scheme",
        state="Maharashtra",
        status="active",
        deadline_date=past_date
    )
    db_session.add(s_expired)

    s_failures = Scheme(
        name="Failure Scheme",
        state="Central",
        status="active",
        source_url="https://central.gov.in/failed-scheme"
    )
    db_session.add(s_failures)
    await db_session.commit()

    # Record 3 fetch failures
    await record_fetch_failure(db_session, "https://central.gov.in/failed-scheme")
    await record_fetch_failure(db_session, "https://central.gov.in/failed-scheme")
    await record_fetch_failure(db_session, "https://central.gov.in/failed-scheme")

    # Run daily maintenance
    m_res = await run_daily_maintenance(db_session)
    assert m_res["expired_count"] == 1
    assert m_res["outdated_count"] == 1

    await db_session.refresh(s_expired)
    await db_session.refresh(s_failures)
    assert s_expired.status == "expired"
    assert s_failures.status == "outdated"
