import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.auth import require_admin
from app.models.user import User
from app.models.scheme import Scheme, SchemeVersion, SourceRecord, SchemeChange, IngestionRun
from app.models.activity import Feedback, Recommendation

router = APIRouter(prefix="/admin", tags=["Admin Dashboard & Management"])

class EditRulesRequest(BaseModel):
    eligibility_rules: Optional[Dict[str, Any]] = None
    benefits: Optional[str] = None
    application_process: Optional[str] = None

@router.get("/overview")
async def get_admin_overview(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Overview metrics:
    - schemes_by_status
    - schemes_by_category
    - unverified_count
    - last_run
    """
    # 1. Schemes by status
    stmt_status = select(Scheme.status, func.count(Scheme.id)).group_by(Scheme.status)
    res_status = await db.execute(stmt_status)
    schemes_by_status = {r[0]: r[1] for r in res_status.all()}

    # 2. Schemes by category
    stmt_cat = select(Scheme.category, func.count(Scheme.id)).group_by(Scheme.category)
    res_cat = await db.execute(stmt_cat)
    schemes_by_category = {r[0] or "Uncategorized": r[1] for r in res_cat.all()}

    # 3. Unverified count
    unverified_count = schemes_by_status.get("unverified", 0)

    # 4. Last ingestion run
    stmt_run = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1)
    res_run = await db.execute(stmt_run)
    last_run_obj = res_run.scalar_one_or_none()
    last_run = None
    if last_run_obj:
        last_run = {
            "id": str(last_run_obj.id),
            "source": last_run_obj.source,
            "started_at": last_run_obj.started_at,
            "finished_at": last_run_obj.finished_at,
            "fetched": last_run_obj.fetched,
            "extracted": last_run_obj.extracted,
            "flagged": last_run_obj.flagged,
            "rejected": last_run_obj.rejected,
            "errors": last_run_obj.errors
        }

    return {
        "schemes_by_status": schemes_by_status,
        "schemes_by_category": schemes_by_category,
        "unverified_count": unverified_count,
        "last_run": last_run
    }

@router.get("/unverified")
async def get_unverified_queue(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Side-by-side view queue of unverified schemes.
    """
    stmt = (
        select(Scheme)
        .options(selectinload(Scheme.source_records))
        .where(Scheme.status == "unverified")
    )
    res = await db.execute(stmt)
    unverified_schemes = res.scalars().all()

    items = []
    for s in unverified_schemes:
        quotes = []
        if s.source_records:
            quotes = [sr.source_url for sr in s.source_records]
        items.append({
            "id": str(s.id),
            "name": s.name,
            "department": s.department,
            "category": s.category,
            "state": s.state,
            "source_url": s.source_url,
            "extraction_confidence": s.extraction_confidence,
            "eligibility_rules": s.eligibility_rules,
            "benefits": s.benefits,
            "source_quotes": quotes
        })
    return items

@router.get("/schemes")
async def list_admin_schemes(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scheme)
    if status_filter:
        stmt = stmt.where(Scheme.status == status_filter)
    
    result = await db.execute(stmt)
    schemes = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "department": s.department,
            "category": s.category,
            "state": s.state,
            "status": s.status,
            "source_url": s.source_url,
            "extraction_confidence": s.extraction_confidence,
            "last_verified": s.last_verified
        }
        for s in schemes
    ]

@router.get("/schemes/{scheme_id}")
async def get_admin_scheme_details(
    scheme_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Scheme)
        .options(
            selectinload(Scheme.versions),
            selectinload(Scheme.source_records)
        )
        .where(Scheme.id == scheme_id)
    )
    result = await db.execute(stmt)
    scheme = result.scalar_one_or_none()

    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    return {
        "id": str(scheme.id),
        "name": scheme.name,
        "description": scheme.description,
        "department": scheme.department,
        "category": scheme.category,
        "state": scheme.state,
        "benefits": scheme.benefits,
        "eligibility_rules": scheme.eligibility_rules,
        "documents": scheme.documents,
        "application_process": scheme.application_process,
        "source_url": scheme.source_url,
        "application_url": scheme.application_url,
        "status": scheme.status,
        "extraction_confidence": scheme.extraction_confidence,
        "versions": [
            {
                "id": str(v.id),
                "content_hash": v.content_hash,
                "fetched_at": v.fetched_at,
                "extracted_json": v.extracted_json
            }
            for v in scheme.versions
        ],
        "source_records": [
            {
                "id": str(sr.id),
                "source_url": sr.source_url,
                "source_type": sr.source_type,
                "content_hash": sr.content_hash,
                "verification_status": sr.verification_status,
                "retrieved_at": sr.retrieved_at
            }
            for sr in scheme.source_records
        ]
    }

@router.post("/schemes/{scheme_id}/verify")
async def verify_scheme(
    scheme_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scheme).where(Scheme.id == scheme_id)
    scheme = (await db.execute(stmt)).scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    scheme.status = "active"
    scheme.last_verified = datetime.now(timezone.utc)
    await db.commit()
    return {"message": f"Scheme '{scheme.name}' verified and marked active.", "scheme_id": str(scheme.id), "status": "active"}

@router.post("/schemes/{scheme_id}/edit-rules")
async def edit_scheme_rules(
    scheme_id: uuid.UUID,
    req: EditRulesRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scheme).where(Scheme.id == scheme_id)
    scheme = (await db.execute(stmt)).scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    if req.eligibility_rules is not None:
        scheme.eligibility_rules = req.eligibility_rules
    if req.benefits is not None:
        scheme.benefits = req.benefits
    if req.application_process is not None:
        scheme.application_process = req.application_process

    await db.commit()
    return {"message": "Scheme rules/details updated successfully", "scheme_id": str(scheme.id)}

@router.post("/schemes/{scheme_id}/reject")
async def reject_scheme(
    scheme_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scheme).where(Scheme.id == scheme_id)
    scheme = (await db.execute(stmt)).scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    scheme.status = "rejected"
    await db.commit()
    return {"message": f"Scheme '{scheme.name}' rejected.", "scheme_id": str(scheme.id), "status": "rejected"}

@router.post("/schemes/{scheme_id}/mark-outdated")
async def mark_scheme_outdated(
    scheme_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scheme).where(Scheme.id == scheme_id)
    scheme = (await db.execute(stmt)).scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    scheme.status = "expired"
    await db.commit()
    return {"message": f"Scheme '{scheme.name}' marked expired/outdated.", "scheme_id": str(scheme.id), "status": "expired"}

@router.get("/changes")
async def get_changes_feed(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(SchemeChange, Scheme.name)
        .join(Scheme, SchemeChange.scheme_id == Scheme.id)
        .order_by(SchemeChange.detected_at.desc())
    )
    res = await db.execute(stmt)
    pairs = res.all()

    return [
        {
            "id": str(c.id),
            "scheme_id": str(c.scheme_id),
            "scheme_name": name,
            "from_version": c.from_version,
            "to_version": c.to_version,
            "diff": c.diff,
            "detected_at": c.detected_at
        }
        for c, name in pairs
    ]

@router.get("/source-health")
async def get_source_health(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scheme)
    res = await db.execute(stmt)
    schemes = res.scalars().all()

    return [
        {
            "scheme_id": str(s.id),
            "scheme_name": s.name,
            "source_url": s.source_url,
            "last_fetched_at": s.last_fetched_at,
            "consecutive_fetch_failures": s.consecutive_fetch_failures,
            "status": s.status
        }
        for s in schemes
    ]

@router.get("/feedback")
async def get_admin_feedback(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Feedback, User.email, User.name)
        .join(User, Feedback.user_id == User.id)
        .order_by(Feedback.created_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    return [
        {
            "id": str(fb.id),
            "user_email": email,
            "user_name": name,
            "recommendation_id": str(fb.recommendation_id),
            "useful": fb.useful,
            "comment": fb.comment,
            "created_at": fb.created_at
        }
        for fb, email, name in rows
    ]

@router.post("/ingest-now")
async def trigger_manual_ingestion(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        from app.ingestion.run import run_ingestion
        # Trigger offline ingestion in background / async
        await run_ingestion(limit=5)
        return {"status": "success", "message": "Manual ingestion run completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ingestion failed: {str(e)}")
