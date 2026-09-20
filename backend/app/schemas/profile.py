from typing import Optional, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

SocialCategoryType = Literal["SC", "ST", "OBC", "EWS", "General", "prefer_not_to_say"]

class ProfileBase(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    rural_urban: Optional[str] = None
    education_level: Optional[str] = None
    course: Optional[str] = None
    year: Optional[str] = None
    occupation: Optional[str] = None
    employment_status: Optional[str] = None
    annual_income: Optional[float] = Field(None, ge=0)
    family_size: Optional[int] = Field(None, ge=1)
    social_category: Optional[SocialCategoryType] = None
    disability: Optional[bool] = None
    minority: Optional[bool] = None
    bpl_card: Optional[bool] = None
    domicile_state: Optional[str] = None
    marital_status: Optional[str] = None
    land_holding_acres: Optional[float] = Field(None, ge=0)
    other_attributes: Optional[Dict[str, Any]] = None

class ProfileUpdate(ProfileBase):
    pass

class ProfileOut(ProfileBase):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)
