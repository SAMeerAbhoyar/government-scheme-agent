from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Literal["user", "admin"] = "user"
    consent: bool = Field(..., description="User explicit consent for data processing")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    consent_given_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
