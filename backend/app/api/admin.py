import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.auth import require_admin
from app.models.user import User
from app.models.scheme import Scheme, SchemeVersion, SourceRecord

router = APIRouter(prefix="/admin", tags=["Admin Scheme Management"])

@router.get("/schemes")
async def list_admin_schemes(
    status_filter: Optional[str] = Query("unverified", alias="status"),
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
    await db.commit()
    return {"message": f"Scheme '{scheme.name}' verified and marked active.", "scheme_id": str(scheme.id), "status": "active"}

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
