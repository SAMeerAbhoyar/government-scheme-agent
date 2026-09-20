import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheme import Scheme, SchemeVersion, SourceRecord, SchemeChunk
from app.agents.extractor import SchemeExtractionOutput, verify_grounding

logger = logging.getLogger(__name__)

async def process_and_save_scheme(
    db: AsyncSession,
    extracted: SchemeExtractionOutput,
    raw_text: str,
    source_url: str,
    content_hash: str,
    source_type: str = "html",
    confidence_threshold: float = 0.8
) -> Tuple[Scheme, bool]:
    """
    Saves or updates a scheme, handles version audit logging, creates source records,
    and calculates verification status based on confidence and grounding verification.
    Returns (scheme, is_new_or_updated)
    """
    # 1. Grounding check
    rules_dict = extracted.eligibility_rules.model_dump()
    all_grounded, ungrounded_quotes = verify_grounding(extracted.eligibility_rules, raw_text)

    # 2. Determine verification status
    is_confident = extracted.extraction_confidence >= confidence_threshold
    if all_grounded and is_confident:
        status_val = "active"
    else:
        status_val = "unverified"
        logger.warning(
            f"Scheme '{extracted.name}' marked unverified. Grounded: {all_grounded}, "
            f"Confidence: {extracted.extraction_confidence}, Ungrounded quotes: {ungrounded_quotes}"
        )

    # 3. Check existing scheme by name or source_url
    stmt = select(Scheme).where(Scheme.source_url == source_url)
    existing_scheme = (await db.execute(stmt)).scalar_one_or_none()

    if not existing_scheme:
        # Check by name
        stmt_name = select(Scheme).where(Scheme.name == extracted.name)
        existing_scheme = (await db.execute(stmt_name)).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    is_updated = False

    if existing_scheme:
        scheme = existing_scheme
        # Update existing fields
        scheme.name = extracted.name
        scheme.description = extracted.description
        scheme.department = extracted.department
        scheme.category = extracted.category
        scheme.state = extracted.state
        scheme.benefits = extracted.benefits
        scheme.eligibility_rules = rules_dict
        scheme.documents = {"items": extracted.documents}
        scheme.application_process = extracted.application_process
        scheme.application_url = extracted.application_url or source_url
        scheme.status = status_val
        scheme.last_verified = now
        scheme.extraction_confidence = extracted.extraction_confidence
    else:
        scheme = Scheme(
            name=extracted.name,
            description=extracted.description,
            department=extracted.department,
            category=extracted.category,
            state=extracted.state,
            benefits=extracted.benefits,
            eligibility_rules=rules_dict,
            documents={"items": extracted.documents},
            application_process=extracted.application_process,
            source_url=source_url,
            application_url=extracted.application_url or source_url,
            status=status_val,
            last_verified=now,
            extraction_confidence=extracted.extraction_confidence
        )
        db.add(scheme)
        await db.flush()
        is_updated = True

    # 4. Handle scheme_versions table on content_hash change
    stmt_version = (
        select(SchemeVersion)
        .where(SchemeVersion.scheme_id == scheme.id)
        .order_by(SchemeVersion.fetched_at.desc())
    )
    versions_res = await db.execute(stmt_version)
    existing_versions = versions_res.scalars().all()

    already_has_version = any(v.content_hash == content_hash for v in existing_versions)

    if not already_has_version:
        new_version = SchemeVersion(
            scheme_id=scheme.id,
            content_hash=content_hash,
            extracted_json={
                "extracted": extracted.model_dump(),
                "grounded": all_grounded,
                "ungrounded_quotes": ungrounded_quotes
            },
            fetched_at=now
        )
        db.add(new_version)
        is_updated = True

        # If previous version existed, compute field-level diff
        if existing_versions:
            latest_prev = existing_versions[0]
            prev_extracted = latest_prev.extracted_json.get("extracted", {})
            from app.services.diff_service import compute_scheme_diff
            from app.models.scheme import SchemeChange

            diff_res = compute_scheme_diff(prev_extracted, extracted.model_dump())
            if diff_res.get("has_changes"):
                change_obj = SchemeChange(
                    scheme_id=scheme.id,
                    from_version=latest_prev.content_hash,
                    to_version=content_hash,
                    diff=diff_res,
                    detected_at=now
                )
                db.add(change_obj)

    # 5. Create source record provenance entry
    source_rec = SourceRecord(
        scheme_id=scheme.id,
        source_url=source_url,
        source_type=source_type,
        retrieved_at=now,
        content_hash=content_hash,
        verification_status=status_val
    )
    db.add(source_rec)

    scheme.consecutive_fetch_failures = 0
    scheme.last_fetched_at = now

    await db.commit()
    await db.refresh(scheme)
    return scheme, is_updated
