# Automated Government Scheme Recommendation Agent

An AI-ready full-stack platform for ingesting, structuring, matching, and recommending government schemes (Central + Maharashtra) for citizens based on deterministic eligibility rules, source citations, and LLM explanations.

---

## Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Citizen / Admin UI      │
                          │   (React + Vite + Tailwind│
                          └─────────────┬─────────────┘
                                        │ REST API (JWT Auth)
                          ┌─────────────▼─────────────┐
                          │     FastAPI Backend       │
                          └──────┬─────────────┬──────┘
                                 │             │
              ┌──────────────────┴──┐       ┌──┴──────────────────┐
              │  Matching Engine    │       │ Hybrid RRF Retriever│
              │  (Deterministic)    │       │ (pgvector + tsv)    │
              └──────────┬──────────┘       └──┬──────────────────┘
                         │                     │
              ┌──────────▼─────────────────────▼──────────┐
              │      PostgreSQL 16 + pgvector Database    │
              └───────────────────────────────────────────┘
```

---

## Tech Stack
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, bcrypt, Fernet AES Encryption
- **Ingestion & Extraction**: Httpx, Trafilatura, BeautifulSoup4, Pdfplumber, Google GenAI (Gemini)
- **RAG & Hybrid Search**: PostgreSQL 16 + `pgvector` (Cosine Similarity) + `tsvector` (Full-Text Search) + Reciprocal Rank Fusion (RRF)
- **Frontend**: React, Vite, Tailwind CSS, React Router v6, Axios, Lucide Icons
- **Deployment**: Docker & Docker Compose
- **Testing & CI**: Pytest (51 passing unit tests), GitHub Actions CI

---

## Quick Setup & Demo (Under 5 Minutes)

### Option 1: Docker Compose (Full Stack Single Command)
```bash
docker-compose up --build -d
```
Then seed the offline demo database:
```bash
cd backend
python -m app.seed_demo
```
- **Frontend URL**: `http://localhost:80`
- **Backend API Docs**: `http://localhost:8000/docs`

---

### Option 2: Local Development Setup

#### 1. Backend Setup
```bash
cd backend
python -m venv venv

# Activate Virtual Environment (Windows)
.\venv\Scripts\Activate.ps1
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
python -m app.seed_demo
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Step-by-Step Live Demo Script

1. **Sign In as Demo Admin**:
   - **Email**: `admin@demo.gov.in`
   - **Password**: `Admin@123`
   - Navigate to `/admin` to view the **Admin Command Center**, system metrics, unverified queue, source health, and changes feed.

2. **Sign In as Demo Persona 1 (Rahul Sharma - Student)**:
   - **Email**: `rahul.student@demo.gov.in`
   - **Password**: `User@123`
   - **Mode 1 Search**: Type query *"scholarship for engineering student in maharashtra"*. View matched schemes, structured match results, and explanations.
   - **Save Scheme**: Click "Save Scheme" to bookmark a scheme.

3. **Sign In as Demo Persona 2 (Ramesh Patil - Farmer)**:
   - **Email**: `ramesh.farmer@demo.gov.in`
   - **Password**: `User@123`
   - **Mode 2 Matching**: Click "Discover by Profile" to run automated profile matching against all active Central & Maharashtra schemes.

4. **Notifications & Change Detection**:
   - Check `/notifications` to see alerts for approaching deadlines, new scheme matches, and scheme version diffs.

---

## Verification & Testing Commands

### 1. Run Complete Pytest Suite (51 Tests)
```bash
cd backend
python -m pytest
```

### 2. Run API Smoke Test Script
```bash
python scripts/smoke_test.py
```

---

## Known Limitations & Production Guidance
- **Domain Scope**: Configured for Central & Maharashtra official portal domains (`.gov.in`, `.nic.in`, `mahadbt.maharashtra.gov.in`).
- **Offline Seeding**: Seeding mode (`seed_demo.py`) works fully offline without requiring active Gemini API keys or live web scraping.
- **Security**: In production, set custom `JWT_SECRET_KEY` and `PROFILE_ENCRYPTION_KEY` in environment variables.

---

## Completion Status
- [x] **Phase 1**: FastAPI backend, PostgreSQL 16 + pgvector, Auth, Profile CRUD, Tri-State Eligibility Engine, React Frontend.
- [x] **Phase 2**: Sources Allowlist, Crawler, LLM Extractor, Grounding Verification, Versioning, Hybrid Search RRF.
- [x] **Phase 3**: Matching Engine (Mode 1 & Mode 2), Recommendation Explainer Agent with Guardrail Fact Inspector, Saved/History/Compare/Feedback.
- [x] **Phase 4**: Change Detection & Version Diffs, Notifications & Deduplication, Admin Dashboard, Hardening (Security Headers, Rate Limiting, Fernet AES Encryption, PII Redaction, No-500 Fallbacks), Docker & Demo Readiness.
