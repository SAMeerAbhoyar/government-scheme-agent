from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class SchemeBase(BaseModel):
    name: str
    description: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    benefits: Optional[str] = None
    eligibility_rules: Optional[Dict[str, Any]] = None
    documents: Optional[Dict[str, Any]] = None
    application_process: Optional[str] = None
    source_url: Optional[str] = None
    application_url: Optional[str] = None
    deadline_date: Optional[datetime] = None
    status: str = "active"
    last_verified: Optional[datetime] = None
    extraction_confidence: Optional[float] = None

class SchemeOut(SchemeBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
