import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.auth import get_current_user
from app.models.user import User, Profile
from app.models.scheme import Scheme
from app.models.activity import SearchHistory, Recommendation
from app.schemas.discovery import ProfileDiscoverRequest, QueryDiscoverRequest, DiscoveryResult, MatchResponse, QuestionItem
from app.services.matching import match_scheme_against_profile, rank_matches, MatchResult
from app.services.questions import get_missing_info_questions
from app.agents.query_planner import QueryPlannerAgent
from app.agents.explainer import RecommendationExplainerAgent, MANDATORY_DISCLAIMER
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discover", tags=["Discovery"])
query_planner = QueryPlannerAgent()
explainer_agent = RecommendationExplainerAgent()
hybrid_retriever = HybridRetriever()

def profile_to_dict(profile: Optional[Profile]) -> Dict[str, Any]:
    if not profile:
        return {}
    data = {}
    for col in Profile.__table__.columns:
        if col.name not in ("id", "user_id"):
            val = getattr(profile, col.name)
            if val is not None:
                if isinstance(val, bool):
                    data[col.name] = val
                elif isinstance(val, (int, float)):
                    data[col.name] = float(val) if isinstance(val, float) else val
                else:
                    data[col.name] = val
    if profile.other_attributes and isinstance(profile.other_attributes, dict):
        data.update(profile.other_attributes)
    return data

@router.post("/profile", response_model=DiscoveryResult)
async def discover_by_profile(
    req: ProfileDiscoverRequest = ProfileDiscoverRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch user profile
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    res = await db.execute(stmt)
    user_profile = res.scalar_one_or_none()
    profile_dict = profile_to_dict(user_profile)

    # 2. Fetch active schemes (and unverified if relevant)
    stmt_schemes = select(Scheme).where(or_(Scheme.status == "active", Scheme.status == "unverified"))
    if req.state_filter:
        stmt_schemes = stmt_schemes.where(or_(Scheme.state == req.state_filter, Scheme.state == "Central"))
    if req.category_filter:
        stmt_schemes = stmt_schemes.where(Scheme.category.ilike(f"%{req.category_filter}%"))

    schemes_res = await db.execute(stmt_schemes)
    schemes = schemes_res.scalars().all()

    # 3. Evaluate deterministic matching
    matches: List[MatchResult] = []
    for s in schemes:
        m = match_scheme_against_profile(profile_dict, s)
        matches.append(m)

    # 4. Rank matches
    ranked_matches = rank_matches(matches)

    # 5. Format responses and generate explanations
    match_responses: List[MatchResponse] = []
    for m in ranked_matches:
        missing_q_dicts = get_missing_info_questions(m.missing_fields)
        missing_questions = [QuestionItem(**q) for q in missing_q_dicts]

        explanation = await explainer_agent.explain(profile_dict, m)

        resp = MatchResponse(
            scheme_id=m.scheme_id,
            scheme_name=m.scheme_name,
            department=m.department,
            category=m.category,
            state=m.state,
            status=m.status,
            unverified=m.unverified,
            extraction_confidence=m.extraction_confidence,
            rule_results=m.rule_results,
            missing_fields=m.missing_fields,
            missing_questions=missing_questions,
            explanation=explanation,
            disclaimer=MANDATORY_DISCLAIMER,
            deadline_date=m.deadline_date,
            source_url=m.source_url,
            application_url=m.application_url,
            match_score=m.match_score
        )
        match_responses.append(resp)

        # Store in Recommendation history
        rec = Recommendation(
            user_id=current_user.id,
            scheme_id=m.scheme_id,
            match_status=m.status,
            reason=explanation[:500] if explanation else m.status
        )
        db.add(rec)

    await db.commit()

    return DiscoveryResult(
        mode="profile",
        query_plan=None,
        total_matches=len(match_responses),
        matches=match_responses
    )

@router.post("/query", response_model=DiscoveryResult)
async def discover_by_query(
    req: QueryDiscoverRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. LLM / Fallback Query Planning
    query_plan = await query_planner.plan_query(req.query)

    # Apply explicit overrides if provided in request
    effective_state = req.state_filter or query_plan.state
    effective_category = req.category_filter or query_plan.category

    # 2. Hybrid Retrieval
    retrieved_chunks = await hybrid_retriever.search(
        db=db,
        query=req.query,
        state_filter=effective_state,
        category_filter=effective_category,
        top_k=10
    )

    scheme_ids = set([c["scheme_id"] for c in retrieved_chunks])

    # Also fetch active schemes matching filters if retrieved list is small
    stmt_schemes = select(Scheme).where(or_(Scheme.status == "active", Scheme.status == "unverified"))
    if effective_state:
        stmt_schemes = stmt_schemes.where(or_(Scheme.state == effective_state, Scheme.state == "Central"))
    if effective_category:
        stmt_schemes = stmt_schemes.where(Scheme.category.ilike(f"%{effective_category}%"))

    filter_schemes_res = await db.execute(stmt_schemes)
    filtered_schemes = filter_schemes_res.scalars().all()
    for s in filtered_schemes:
        scheme_ids.add(str(s.id))

    if scheme_ids:
        all_schemes_res = await db.execute(select(Scheme).where(Scheme.id.in_(list(scheme_ids))))
        schemes = all_schemes_res.scalars().all()
    else:
        schemes = []

    # 3. User Profile
    stmt_prof = select(Profile).where(Profile.user_id == current_user.id)
    prof_res = await db.execute(stmt_prof)
    user_profile = prof_res.scalar_one_or_none()
    profile_dict = profile_to_dict(user_profile)

    # 4. Deterministic Matching
    matches: List[MatchResult] = []
    for s in schemes:
        m = match_scheme_against_profile(profile_dict, s)
        matches.append(m)

    # 5. Rank
    ranked_matches = rank_matches(matches)

    # 6. Format responses & Explanations
    match_responses: List[MatchResponse] = []
    for m in ranked_matches:
        missing_q_dicts = get_missing_info_questions(m.missing_fields)
        missing_questions = [QuestionItem(**q) for q in missing_q_dicts]

        explanation = await explainer_agent.explain(profile_dict, m)

        resp = MatchResponse(
            scheme_id=m.scheme_id,
            scheme_name=m.scheme_name,
            department=m.department,
            category=m.category,
            state=m.state,
            status=m.status,
            unverified=m.unverified,
            extraction_confidence=m.extraction_confidence,
            rule_results=m.rule_results,
            missing_fields=m.missing_fields,
            missing_questions=missing_questions,
            explanation=explanation,
            disclaimer=MANDATORY_DISCLAIMER,
            deadline_date=m.deadline_date,
            source_url=m.source_url,
            application_url=m.application_url,
            match_score=m.match_score
        )
        match_responses.append(resp)

    # Record search history
    history = SearchHistory(
        user_id=current_user.id,
        mode="query",
        query=req.query,
        category=effective_category
    )
    db.add(history)
    await db.commit()

    return DiscoveryResult(
        mode="query",
        query_plan=query_plan.model_dump(),
        total_matches=len(match_responses),
        matches=match_responses
    )
