import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    benefits: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    eligibility_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    documents: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    application_process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    deadline_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    last_verified: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    consecutive_fetch_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    versions: Mapped[list["SchemeVersion"]] = relationship("SchemeVersion", back_populates="scheme", cascade="all, delete-orphan")
    chunks: Mapped[list["SchemeChunk"]] = relationship("SchemeChunk", back_populates="scheme", cascade="all, delete-orphan")
    source_records: Mapped[list["SourceRecord"]] = relationship("SourceRecord", back_populates="scheme", cascade="all, delete-orphan")
    saved_by: Mapped[list["SavedScheme"]] = relationship("SavedScheme", back_populates="scheme", cascade="all, delete-orphan")
    changes: Mapped[list["SchemeChange"]] = relationship("SchemeChange", back_populates="scheme", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship("Recommendation", back_populates="scheme", cascade="all, delete-orphan")

class SchemeChange(Base):
    __tablename__ = "scheme_changes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scheme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False)
    from_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    to_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    diff: Mapped[dict] = mapped_column(JSON, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="changes")

class SchemeVersion(Base):
    __tablename__ = "scheme_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scheme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="versions")

class SchemeChunk(Base):
    __tablename__ = "scheme_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scheme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False)
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    embedding: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tsv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="chunks")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scheme_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("schemes.id", ondelete="SET NULL"), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    scheme: Mapped[Optional["Scheme"]] = relationship("Scheme", back_populates="source_records")

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flagged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
