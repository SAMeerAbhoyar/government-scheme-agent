import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.auth import get_current_user
from app.models.user import User, Profile
from app.models.scheme import Scheme
from app.models.activity import SavedScheme, SearchHistory, Recommendation, Feedback
from app.schemas.user_features import (
    SavedSchemeOut, SearchHistoryOut, RecommendationHistoryOut,
    CompareRequest, SchemeCompareItem, CompareMatrixResponse,
    FeedbackCreate, FeedbackOut
)
from app.services.matching import match_scheme_against_profile
from app.api.discovery import profile_to_dict

logger = logging.getLogger(__name__)

router = APIRouter(tags=["User Features"])

# --- Bookmarks / Saved Schemes ---

@router.post("/schemes/{scheme_id}/save", response_model=SavedSchemeOut, status_code=status.HTTP_201_CREATED)
async def save_scheme(
    scheme_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check scheme exists
    scheme_res = await db.execute(select(Scheme).where(Scheme.id == scheme_id))
    scheme = scheme_res.scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    # Check if already saved
    saved_res = await db.execute(
        select(SavedScheme).where(SavedScheme.user_id == current_user.id, SavedScheme.scheme_id == scheme_id)
    )
    existing = saved_res.scalar_one_or_none()
    if existing:
        return SavedSchemeOut(
            id=existing.id,
            scheme_id=existing.scheme_id,
            scheme_name=scheme.name,
            category=scheme.category,
            state=scheme.state,
            source_url=scheme.source_url,
            saved_at=existing.saved_at
        )

    saved = SavedScheme(user_id=current_user.id, scheme_id=scheme_id)
    db.add(saved)
    await db.commit()
    await db.refresh(saved)

    return SavedSchemeOut(
        id=saved.id,
        scheme_id=saved.scheme_id,
        scheme_name=scheme.name,
        category=scheme.category,
        state=scheme.state,
        source_url=scheme.source_url,
        saved_at=saved.saved_at
    )

@router.delete("/schemes/{scheme_id}/save", status_code=status.HTTP_200_OK)
async def unsave_scheme(
    scheme_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = delete(SavedScheme).where(SavedScheme.user_id == current_user.id, SavedScheme.scheme_id == scheme_id)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved scheme bookmark not found")
    return {"message": "Scheme removed from saved bookmarks."}

@router.get("/schemes/saved", response_model=List[SavedSchemeOut])
async def get_saved_schemes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SavedScheme, Scheme).join(Scheme, SavedScheme.scheme_id == Scheme.id).where(SavedScheme.user_id == current_user.id)
    res = await db.execute(stmt)
    rows = res.all()

    out = []
    for saved, scheme in rows:
        out.append(SavedSchemeOut(
            id=saved.id,
            scheme_id=saved.scheme_id,
            scheme_name=scheme.name,
            category=scheme.category,
            state=scheme.state,
            source_url=scheme.source_url,
            saved_at=saved.saved_at
        ))
    return out

# --- History ---

@router.get("/history/search", response_model=List[SearchHistoryOut])
async def get_search_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SearchHistory).where(SearchHistory.user_id == current_user.id).order_by(SearchHistory.created_at.desc()).limit(50)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/history/recommendations", response_model=List[RecommendationHistoryOut])
async def get_recommendation_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Recommendation, Scheme).join(Scheme, Recommendation.scheme_id == Scheme.id).where(Recommendation.user_id == current_user.id).order_by(Recommendation.created_at.desc()).limit(50)
    res = await db.execute(stmt)
    rows = res.all()

    out = []
    for rec, scheme in rows:
        out.append(RecommendationHistoryOut(
            id=rec.id,
            scheme_id=rec.scheme_id,
            scheme_name=scheme.name,
            match_status=rec.match_status,
            reason=rec.reason,
            created_at=rec.created_at
        ))
    return out

# --- Side-by-Side Scheme Comparison Matrix ---

@router.post("/schemes/compare", response_model=CompareMatrixResponse)
async def compare_schemes(
    req: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if len(req.scheme_ids) < 2 or len(req.scheme_ids) > 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Side-by-side comparison requires between 2 and 4 schemes.")

    # Fetch user profile
    stmt_prof = select(Profile).where(Profile.user_id == current_user.id)
    prof_res = await db.execute(stmt_prof)
    user_profile = prof_res.scalar_one_or_none()
    profile_dict = profile_to_dict(user_profile)

    # Fetch schemes
    schemes_res = await db.execute(select(Scheme).where(Scheme.id.in_(req.scheme_ids)))
    schemes = schemes_res.scalars().all()

    if len(schemes) != len(req.scheme_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more specified schemes were not found.")

    comparison_items = []
    for s in schemes:
        m = match_scheme_against_profile(profile_dict, s)
        
        matched_count = sum(1 for r in m.rule_results if r.result == "match")
        failed_count = sum(1 for r in m.rule_results if r.result == "no_match")
        unknown_count = sum(1 for r in m.rule_results if r.result == "unknown")

        rule_summaries = [r.model_dump() for r in m.rule_results]

        item = SchemeCompareItem(
            scheme_id=s.id,
            name=s.name,
            state=s.state,
            category=s.category,
            department=s.department,
            summary=s.summary,
            benefits=s.benefits,
            application_url=s.application_url or s.source_url,
            source_url=s.source_url,
            match_status=m.status,
            matched_rules_count=matched_count,
            failed_rules_count=failed_count,
            unknown_rules_count=unknown_count,
            rule_summary=rule_summaries
        )
        comparison_items.append(item)

    return CompareMatrixResponse(
        comparison=comparison_items,
        note="Comparison matrix provides factual rule evaluations without ranking or declaring any single scheme as best."
    )

# --- Feedback ---

@router.post("/recommendations/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    fb_in: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    rec_id = fb_in.recommendation_id
    if not rec_id:
        # Create a dummy recommendation row if feedback given directly on scheme
        if not fb_in.scheme_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide recommendation_id or scheme_id")
        rec = Recommendation(
            user_id=current_user.id,
            scheme_id=fb_in.scheme_id,
            match_status="user_feedback",
            reason="Direct feedback"
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        rec_id = rec.id

    fb = Feedback(
        user_id=current_user.id,
        recommendation_id=rec_id,
        useful=fb_in.useful,
        comment=fb_in.comment
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb

# --- Scheme Detail ---

@router.get("/schemes/{scheme_id}", response_model=dict)
async def get_scheme_detail(
    scheme_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scheme).where(Scheme.id == scheme_id)
    res = await db.execute(stmt)
    scheme = res.scalar_one_or_none()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    # Also evaluate user's profile against scheme
    stmt_prof = select(Profile).where(Profile.user_id == current_user.id)
    prof_res = await db.execute(stmt_prof)
    user_profile = prof_res.scalar_one_or_none()
    profile_dict = profile_to_dict(user_profile)

    m = match_scheme_against_profile(profile_dict, scheme)

    # Check if saved
    saved_res = await db.execute(
        select(SavedScheme).where(SavedScheme.user_id == current_user.id, SavedScheme.scheme_id == scheme_id)
    )
    is_saved = saved_res.scalar_one_or_none() is not None

    return {
        "id": str(scheme.id),
        "name": scheme.name,
        "department": scheme.department,
        "category": scheme.category,
        "state": scheme.state,
        "summary": scheme.summary,
        "benefits": scheme.benefits,
        "eligibility_summary": scheme.eligibility_summary,
        "eligibility_rules": scheme.eligibility_rules,
        "application_process": scheme.application_process,
        "documents_required": scheme.documents_required,
        "deadline_date": scheme.deadline_date,
        "source_url": scheme.source_url,
        "application_url": scheme.application_url,
        "status": scheme.status,
        "extraction_confidence": scheme.extraction_confidence,
        "is_saved": is_saved,
        "user_match": m.model_dump()
    }
