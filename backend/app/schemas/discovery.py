from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from app.services.matching import RuleResultDetail

class ProfileDiscoverRequest(BaseModel):
    category_filter: Optional[str] = None
    state_filter: Optional[str] = None

class QueryDiscoverRequest(BaseModel):
    query: str
    category_filter: Optional[str] = None
    state_filter: Optional[str] = None

class QuestionItem(BaseModel):
    field: str
    category: str
    question_text: str
    input_type: str
    placeholder: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None

class MatchResponse(BaseModel):
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
    missing_questions: List[QuestionItem] = []
    explanation: Optional[str] = None
    disclaimer: str
    deadline_date: Optional[datetime] = None
    source_url: Optional[str] = None
    application_url: Optional[str] = None
    match_score: float = 0.0

class DiscoveryResult(BaseModel):
    mode: str # query | profile
    query_plan: Optional[Dict[str, Any]] = None
    total_matches: int
    matches: List[MatchResponse]
