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

def safe_match_scheme_against_profile(profile_data: Dict[str, Any], scheme: Scheme) -> MatchResult:
    """
    Safely matches a scheme against a profile data dict.
    On any error, returns status 'cannot_determine' with reason 'Could not evaluate this scheme',
    logs the error, and continues so one bad scheme cannot break the whole search.
    """
    try:
        return match_scheme_against_profile(profile_data, scheme)
    except Exception as e:
        logger.error(f"Error matching scheme '{getattr(scheme, 'name', 'unknown')}' ({getattr(scheme, 'id', '')}): {e}", exc_info=True)
        return MatchResult(
            scheme_id=str(getattr(scheme, "id", "")),
            scheme_name=getattr(scheme, "name", "Government Scheme"),
            department=getattr(scheme, "department", "Government Portal"),
            category=getattr(scheme, "category", "General"),
            state=getattr(scheme, "state", "Central"),
            status="cannot_determine",
            unverified=(getattr(scheme, "status", "") == "unverified"),
            extraction_confidence=getattr(scheme, "extraction_confidence", None),
            rule_results=[],
            missing_fields=[],
            deadline_date=getattr(scheme, "deadline_date", None),
            source_url=getattr(scheme, "source_url", None),
            application_url=getattr(scheme, "application_url", None) or getattr(scheme, "source_url", None),
            match_score=30.0
        )

def match_scheme_against_profile(profile_data: Dict[str, Any], scheme: Scheme) -> MatchResult:
    try:
        rules = getattr(scheme, "eligibility_rules", {}) or {}
        eval_res: SchemeEvaluationResult = evaluate_eligibility(rules, profile_data or {})

        rule_results: List[RuleResultDetail] = []
        missing_fields_set = set()
        no_match_count = 0
        unknown_count = 0
        match_count = 0

        for detail in eval_res.details:
            f_name = str(detail.field) if detail.field is not None else "unknown"
            rule_results.append(RuleResultDetail(
                field=f_name,
                op=str(detail.op),
                required_value=detail.expected_value,
                user_value=detail.actual_value,
                result=detail.status.value if hasattr(detail.status, "value") else str(detail.status),
                source_quote=detail.source_quote
            ))

            if detail.status == EvaluationStatus.NO_MATCH:
                no_match_count += 1
            elif detail.status == EvaluationStatus.UNKNOWN:
                unknown_count += 1
                missing_fields_set.add(f_name)
            elif detail.status == EvaluationStatus.MATCH:
                match_count += 1

        if no_match_count > 0:
            match_status = "not_matching"
        elif unknown_count > 0:
            match_status = "cannot_determine"
        else:
            match_status = "potentially_relevant"

        status_weights = {
            "potentially_relevant": 100.0,
            "cannot_determine": 50.0,
            "not_matching": 0.0
        }
        score = status_weights[match_status]
        score -= (len(missing_fields_set) * 5.0)

        is_unverified = (getattr(scheme, "status", "") == "unverified")
        if is_unverified:
            score -= 20.0

        return MatchResult(
            scheme_id=str(getattr(scheme, "id", "")),
            scheme_name=getattr(scheme, "name", "Government Scheme"),
            department=getattr(scheme, "department", "Government Portal"),
            category=getattr(scheme, "category", "General"),
            state=getattr(scheme, "state", "Central"),
            status=match_status,
            unverified=is_unverified,
            extraction_confidence=getattr(scheme, "extraction_confidence", None),
            rule_results=rule_results,
            missing_fields=sorted(list(missing_fields_set)),
            deadline_date=getattr(scheme, "deadline_date", None),
            source_url=getattr(scheme, "source_url", None),
            application_url=getattr(scheme, "application_url", None) or getattr(scheme, "source_url", None),
            match_score=max(0.0, score)
        )
    except Exception as e:
        logger.error(f"Error in match_scheme_against_profile for scheme {getattr(scheme, 'id', '')}: {e}", exc_info=True)
        return MatchResult(
            scheme_id=str(getattr(scheme, "id", "")),
            scheme_name=getattr(scheme, "name", "Government Scheme"),
            department=getattr(scheme, "department", "Government Portal"),
            category=getattr(scheme, "category", "General"),
            state=getattr(scheme, "state", "Central"),
            status="cannot_determine",
            unverified=(getattr(scheme, "status", "") == "unverified"),
            extraction_confidence=getattr(scheme, "extraction_confidence", None),
            rule_results=[],
            missing_fields=[],
            deadline_date=getattr(scheme, "deadline_date", None),
            source_url=getattr(scheme, "source_url", None),
            application_url=getattr(scheme, "application_url", None) or getattr(scheme, "source_url", None),
            match_score=30.0
        )

def rank_matches(matches: List[MatchResult]) -> List[MatchResult]:
    status_order = {
        "potentially_relevant": 0,
        "cannot_determine": 1,
        "not_matching": 2
    }

    def sort_key(m: MatchResult):
        s_rank = status_order.get(m.status, 3)
        v_rank = 1 if m.unverified else 0
        missing_count = len(m.missing_fields)
        deadline_ts = m.deadline_date.timestamp() if (m.deadline_date and hasattr(m.deadline_date, "timestamp")) else float('inf')
        return (s_rank, v_rank, missing_count, deadline_ts)

    try:
        return sorted(matches, key=sort_key)
    except Exception as e:
        logger.error(f"Error ranking matches: {e}")
        return matches
