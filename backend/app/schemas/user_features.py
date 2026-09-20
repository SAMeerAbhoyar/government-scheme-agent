import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SavedSchemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_name: str
    category: Optional[str] = None
    state: Optional[str] = None
    source_url: Optional[str] = None
    saved_at: datetime

class SearchHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mode: str
    query: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime

class RecommendationHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_name: str
    match_status: str
    reason: Optional[str] = None
    created_at: datetime

class CompareRequest(BaseModel):
    scheme_ids: List[uuid.UUID]

class SchemeCompareItem(BaseModel):
    scheme_id: uuid.UUID
    name: str
    state: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    summary: Optional[str] = None
    benefits: Optional[str] = None
    application_url: Optional[str] = None
    source_url: Optional[str] = None
    match_status: str
    matched_rules_count: int
    failed_rules_count: int
    unknown_rules_count: int
    rule_summary: List[Dict[str, Any]]

class CompareMatrixResponse(BaseModel):
    comparison: List[SchemeCompareItem]
    note: str = "Comparison matrix provides factual rule evaluations without ranking or declaring any single scheme as best."

class FeedbackCreate(BaseModel):
    recommendation_id: Optional[uuid.UUID] = None
    scheme_id: Optional[uuid.UUID] = None
    useful: bool
    comment: Optional[str] = None

class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    useful: bool
    comment: Optional[str] = None
    created_at: datetime
