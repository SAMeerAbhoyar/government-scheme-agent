import pytest
from sqlalchemy import select
from httpx import AsyncClient
from app.agents.extractor import MockLLMProvider
from app.services.scheme_service import process_and_save_scheme
from app.models.scheme import Scheme, SchemeVersion, SourceRecord

@pytest.mark.asyncio
async def test_scheme_upsert_and_versioning(db_session):
    raw_doc_v1 = "Post Matric Scholarship for Engineering Students in Maharashtra. Income under 2.5 lakh."
    url = "https://maharashtra.gov.in/scholarship"
    hash_v1 = "hash_v1_12345"

    provider = MockLLMProvider()
    extracted_v1 = await provider.extract_scheme(raw_doc_v1, url)

    # 1. First save
    scheme, is_updated = await process_and_save_scheme(
        db=db_session,
        extracted=extracted_v1,
        raw_text=raw_doc_v1,
        source_url=url,
        content_hash=hash_v1
    )
    assert scheme.id is not None
    assert is_updated is True

    # Verify versions table
    stmt_v = select(SchemeVersion).where(SchemeVersion.scheme_id == scheme.id)
    versions = (await db_session.execute(stmt_v)).scalars().all()
    assert len(versions) == 1
    assert versions[0].content_hash == hash_v1

    # 2. Second save with NEW content hash
    raw_doc_v2 = "Updated Post Matric Scholarship for Engineering Students in Maharashtra. Income under 2.5 lakh."
    hash_v2 = "hash_v2_67890"

    extracted_v2 = await provider.extract_scheme(raw_doc_v2, url)
    scheme_v2, is_updated_v2 = await process_and_save_scheme(
        db=db_session,
        extracted=extracted_v2,
        raw_text=raw_doc_v2,
        source_url=url,
        content_hash=hash_v2
    )

    # Verify version audit logging created a second version entry
    versions_after = (await db_session.execute(stmt_v)).scalars().all()
    assert len(versions_after) == 2
    hashes = [v.content_hash for v in versions_after]
    assert hash_v1 in hashes
    assert hash_v2 in hashes
