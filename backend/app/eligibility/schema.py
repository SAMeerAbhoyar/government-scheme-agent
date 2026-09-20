from enum import Enum
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field

class OperatorEnum(str, Enum):
    EQ = "=="
    NEQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"

class EvaluationStatus(str, Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    UNKNOWN = "unknown"

class RuleLeaf(BaseModel):
    field: str
    op: OperatorEnum
    value: Any
    unit: Optional[str] = None
    source_quote: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    verified: bool = True

class RuleGroup(BaseModel):
    all_of: Optional[List[Union[RuleLeaf, 'RuleGroup']]] = None
    any_of: Optional[List[Union[RuleLeaf, 'RuleGroup']]] = None
    not_of: Optional[Union[RuleLeaf, 'RuleGroup']] = None

RuleGroup.model_rebuild()

class LeafEvaluationDetail(BaseModel):
    field: str
    op: str
    expected_value: Any
    actual_value: Any
    status: EvaluationStatus
    source_quote: Optional[str] = None

class SchemeEvaluationResult(BaseModel):
    overall_status: EvaluationStatus
    summary_reason: str
    details: List[LeafEvaluationDetail] = []
