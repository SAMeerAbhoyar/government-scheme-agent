import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.models.scheme import Scheme
from app.eligibility.schema import (
    RuleGroup, RuleLeaf, EvaluationStatus, SchemeEvaluationResult, LeafEvaluationDetail
)
from app.eligibility.evaluator import evaluate_eligibility, evaluate_node

logger = logging.getLogger(__name__)

class RuleResultDetail(BaseModel):
    field: str
    op: str
    required_value: Any
    user_value: Any
    result: str # match / no_match / unknown
    source_quote: Optional[str] = None

class MatchResult(BaseModel):
    scheme_id: str
    scheme_name: str
    department: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    status: str # potentially_relevant | cannot_determine | not_matching
    unverified: bool = False
    extraction_confidence: Optional[float] = None
    rule_results: List[RuleResultDetail] = []
    missing_fields: List[str] = []
    deadline_date: Optional[datetime] = None
    source_url: Optional[str] = None
    application_url: Optional[str] = None
    match_score: float = 0.0

def match_scheme_against_profile(profile_data: Dict[str, Any], scheme: Scheme) -> MatchResult:
    rules = scheme.eligibility_rules or {}
    
    # Run deterministic eligibility evaluator
    eval_res: SchemeEvaluationResult = evaluate_eligibility(rules, profile_data)
    
    rule_results: List[RuleResultDetail] = []
    missing_fields_set = set()
    no_match_count = 0
    unknown_count = 0
    match_count = 0

    for detail in eval_res.details:
        rule_results.append(RuleResultDetail(
            field=detail.field,
            op=detail.op,
            required_value=detail.expected_value,
            user_value=detail.actual_value,
            result=detail.status.value,
            source_quote=detail.source_quote
        ))
        
        if detail.status == EvaluationStatus.NO_MATCH:
            no_match_count += 1
        elif detail.status == EvaluationStatus.UNKNOWN:
            unknown_count += 1
            missing_fields_set.add(detail.field)
        elif detail.status == EvaluationStatus.MATCH:
            match_count += 1

    # Status classification:
    # not_matching: if ANY rule is NO_MATCH
    # cannot_determine: if NO rule is NO_MATCH, but at least one rule is UNKNOWN
    # potentially_relevant: if all evaluated rules pass (0 NO_MATCH and 0 UNKNOWN)
    if no_match_count > 0:
        match_status = "not_matching"
    elif unknown_count > 0:
        match_status = "cannot_determine"
    else:
        match_status = "potentially_relevant"

    # Score calculation for tie-breaking
    # Base score by status
    status_weights = {
        "potentially_relevant": 100.0,
        "cannot_determine": 50.0,
        "not_matching": 0.0
    }
    score = status_weights[match_status]
    
    # Deduct for unknowns
    score -= (len(missing_fields_set) * 5.0)
    
    # Deduct for unverified scheme
    is_unverified = scheme.status == "unverified"
    if is_unverified:
        score -= 20.0

    return MatchResult(
        scheme_id=str(scheme.id),
        scheme_name=scheme.name,
        department=scheme.department,
        category=scheme.category,
        state=scheme.state,
        status=match_status,
        unverified=is_unverified,
        extraction_confidence=scheme.extraction_confidence,
        rule_results=rule_results,
        missing_fields=sorted(list(missing_fields_set)),
        deadline_date=scheme.deadline_date,
        source_url=scheme.source_url,
        application_url=scheme.application_url or scheme.source_url,
        match_score=max(0.0, score)
    )

def rank_matches(matches: List[MatchResult]) -> List[MatchResult]:
    """
    Ranks matches according to strict priority:
    1. Status: potentially_relevant > cannot_determine > not_matching
    2. Verification: Active (verified) > Unverified
    3. Fewer missing fields (fewer unknowns)
    4. Nearest deadline date
    """
    status_order = {
        "potentially_relevant": 0,
        "cannot_determine": 1,
        "not_matching": 2
    }

    def sort_key(m: MatchResult):
        s_rank = status_order.get(m.status, 3)
        v_rank = 1 if m.unverified else 0
        missing_count = len(m.missing_fields)
        
        # Deadline timestamp (none = infinity)
        deadline_ts = m.deadline_date.timestamp() if m.deadline_date else float('inf')
        
        return (s_rank, v_rank, missing_count, deadline_ts)

    return sorted(matches, key=sort_key)
