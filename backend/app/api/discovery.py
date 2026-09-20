import uuid
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
from app.services.matching import match_scheme_against_profile, safe_match_scheme_against_profile, rank_matches, MatchResult
from app.services.questions import get_missing_info_questions
from app.agents.query_planner import QueryPlannerAgent
from app.agents.explainer import RecommendationExplainerAgent, MANDATORY_DISCLAIMER, generate_template_explanation
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discover", tags=["Discovery"])
query_planner = QueryPlannerAgent()
explainer_agent = RecommendationExplainerAgent()
hybrid_retriever = HybridRetriever()

CATEGORY_KEYWORDS = {
    'Agriculture': ['agriculture', 'farm', 'kisan', 'shetkari', 'crop', 'pashu'],
    'Girl child': ['girl', 'kanya', 'child', 'daughter', 'balika', 'girl child'],
    'Women': ['women', 'woman', 'mahila', 'female', 'girl', 'kanya', 'matru'],
    'Scholarship and education': ['education', 'scholarship', 'shikshan', 'shishyavrutti', 'student', 'school', 'college', 'matric'],
    'Old age': ['old', 'senior', 'pension', 'vaya', 'vayu', 'elderly', 'vridha'],
    'Poor and BPL support': ['poor', 'bpl', 'welfare', 'subsid', 'ration', 'antodaya', 'social welfare', 'garib', 'poverty'],
    'Health': ['health', 'arogya', 'medical', 'hospital', 'swasthya', 'bima', 'insurance', 'matru'],
    'Housing': ['housing', 'awas', 'gharkul', 'shelter', 'house', 'pmay'],
    'Employment': ['employment', 'job', 'rozgar', 'skill', 'entrepreneur', 'kaushal', 'business', 'mudra', 'standup']
}

def build_category_clause(category_filter: Optional[str]):
    if not category_filter or category_filter in ("All", "All categories"):
        return None
    kws = CATEGORY_KEYWORDS.get(category_filter, [category_filter.lower()])
    conds = []
    for kw in kws:
        conds.append(Scheme.category.ilike(f"%{kw}%"))
        conds.append(Scheme.name.ilike(f"%{kw}%"))
        conds.append(Scheme.description.ilike(f"%{kw}%"))
    return or_(*conds)

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
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    res = await db.execute(stmt)
    user_profile = res.scalar_one_or_none()
    profile_dict = profile_to_dict(user_profile)

    stmt_schemes = select(Scheme).where(or_(Scheme.status == "active", Scheme.status == "unverified"))
    if req.state_filter:
        stmt_schemes = stmt_schemes.where(or_(Scheme.state == req.state_filter, Scheme.state == "Central"))

    cat_clause = build_category_clause(req.category_filter)
    if cat_clause is not None:
        stmt_schemes = stmt_schemes.where(cat_clause)

    schemes_res = await db.execute(stmt_schemes)
    schemes = schemes_res.scalars().all()

    matches: List[MatchResult] = []
    for s in schemes:
        m = safe_match_scheme_against_profile(profile_dict, s)
        matches.append(m)

    ranked_matches = rank_matches(matches)

    match_responses: List[MatchResponse] = []
    for m in ranked_matches:
        missing_q_dicts = get_missing_info_questions(m.missing_fields)
        missing_questions = [QuestionItem(**q) for q in missing_q_dicts]

        try:
            explanation = await explainer_agent.explain(profile_dict, m)
        except Exception as e_exp:
            logger.warning(f"Error generating explanation for scheme {m.scheme_id}: {e_exp}")
            explanation = generate_template_explanation(m)

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

        rec = Recommendation(
            user_id=current_user.id,
            scheme_id=uuid.UUID(str(m.scheme_id)),
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
    query_text = (req.query or "").strip()
    cat_filter = req.category_filter if req.category_filter and req.category_filter not in ("All", "All categories") else None

    stmt_base = select(Scheme).where(or_(Scheme.status == "active", Scheme.status == "unverified"))
    if req.state_filter:
        stmt_base = stmt_base.where(or_(Scheme.state == req.state_filter, Scheme.state == "Central"))

    cat_clause = build_category_clause(cat_filter)
    if cat_clause is not None:
        stmt_base = stmt_base.where(cat_clause)

    base_res = await db.execute(stmt_base)
    base_schemes = base_res.scalars().all()
    base_schemes_by_id = {str(s.id): s for s in base_schemes}

    query_plan_dict = None
    target_schemes = []

    if not query_text:
        target_schemes = base_schemes
        query_plan_dict = {"query": "", "intent": "category_browse", "category": cat_filter}
    else:
        retrieved_scheme_ids = []
        try:
            query_plan = await query_planner.plan_query(query_text)
            query_plan_dict = query_plan.model_dump()

            retrieved_chunks = await hybrid_retriever.search(
                db=db,
                query=query_text,
                state_filter=req.state_filter or query_plan.state,
                category_filter=cat_filter or query_plan.category,
                top_k=15
            )
            retrieved_scheme_ids = [c["scheme_id"] for c in retrieved_chunks]
        except Exception as e:
            logger.warning(f"Query planner / hybrid retriever failed: {e}. Falling back to SQL keyword search.")

        matched_set = {}
        for sid in retrieved_scheme_ids:
            if sid in base_schemes_by_id:
                matched_set[sid] = base_schemes_by_id[sid]

        words = [w.lower() for w in query_text.split() if len(w) > 2]
        for s in base_schemes:
            if str(s.id) not in matched_set:
                full_text = f"{s.name} {s.category} {s.description} {s.department}".lower()
                if any(w in full_text for w in words):
                    matched_set[str(s.id)] = s

        if matched_set:
            target_schemes = list(matched_set.values())
        else:
            target_schemes = base_schemes

    stmt_prof = select(Profile).where(Profile.user_id == current_user.id)
    prof_res = await db.execute(stmt_prof)
    user_profile = prof_res.scalar_one_or_none()
    profile_dict = profile_to_dict(user_profile)

    matches: List[MatchResult] = []
    for s in target_schemes:
        m = safe_match_scheme_against_profile(profile_dict, s)
        matches.append(m)

    ranked_matches = rank_matches(matches)

    match_responses: List[MatchResponse] = []
    for m in ranked_matches:
        missing_q_dicts = get_missing_info_questions(m.missing_fields)
        missing_questions = [QuestionItem(**q) for q in missing_q_dicts]

        try:
            explanation = await explainer_agent.explain(profile_dict, m)
        except Exception as e_exp:
            logger.warning(f"Error generating explanation for scheme {m.scheme_id}: {e_exp}")
            explanation = generate_template_explanation(m)

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

    history = SearchHistory(
        user_id=current_user.id,
        mode="query",
        query=query_text or f"Category: {cat_filter or 'All'}",
        category=cat_filter
    )
    db.add(history)
    await db.commit()

    return DiscoveryResult(
        mode="query",
        query_plan=query_plan_dict,
        total_matches=len(match_responses),
        matches=match_responses
    )
