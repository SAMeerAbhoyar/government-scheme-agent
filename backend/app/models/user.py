import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, Boolean, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    consent_given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    profile: Mapped[Optional["Profile"]] = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    saved_schemes: Mapped[list["SavedScheme"]] = relationship("SavedScheme", back_populates="user", cascade="all, delete-orphan")
    search_history: Mapped[list["SearchHistory"]] = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    feedback: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rural_urban: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    education_level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    course: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    year: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employment_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    annual_income: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    family_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    social_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # SC, ST, OBC, EWS, General, prefer_not_to_say
    disability: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    minority: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    bpl_card: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    domicile_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    land_holding_acres: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    other_attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="profile")
