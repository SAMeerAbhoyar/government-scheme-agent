# Automated Government Scheme Recommendation Agent

An AI-ready platform for ingesting, structuring, matching, and recommending government schemes (Central + Maharashtra) for citizens based on deterministic eligibility rules and source citations.

## Tech Stack
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, bcrypt
- **Ingestion & Extraction**: Httpx, Trafilatura, BeautifulSoup4, Pdfplumber, Google GenAI (Gemini)
- **RAG & Hybrid Search**: PostgreSQL 16 + `pgvector` (Cosine Similarity) + `tsvector` (Full-Text Search) + Reciprocal Rank Fusion (RRF)
- **Frontend**: React, Vite, Tailwind CSS, React Router v6, Axios
- **Testing**: Pytest, Pytest-asyncio

---

## Quick Setup & Execution Guide

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 2. Environment Setup
```bash
cd government-scheme-agent
cp .env.example .env
```

### 3. Start PostgreSQL Database
```bash
docker-compose up -d
```

### 4. Backend Setup & Migrations
```bash
cd backend

# Create virtual environment
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1
# Linux/macOS
source venv/bin/activate

# Install Phase 1 + Phase 2 dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Run backend server
uvicorn app.main:app --reload --port 8000
```
Backend API interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Phase 2 Commands (Offline Ingestion & Hybrid Search)

### 1. Run Offline Ingestion CLI
Ingest 20 official Central & Maharashtra government schemes from allowlisted domain sources (`sources.yaml`):
```bash
cd backend
python -m app.ingestion.run --limit 20
```
*Optional CLI Flags*:
- `--source <id>`: Ingest a single source by ID (e.g. `src-04-mahadbt-rajarshi-shahu`).
- `--limit N`: Limit ingestion to $N$ sources.
- `--reindex`: Clear existing vector embeddings and re-chunk document sections.

### 2. Run Test Hybrid Search Query
Search pre-ingested schemes using hybrid RRF retrieval:
```bash
python -m app.ingestion.test_search
```

### 3. API Hybrid Search Endpoint
`GET /schemes/search?q=scholarship+for+engineering+students+Maharashtra&state=Maharashtra` (Requires Bearer JWT token):
```bash
curl -H "Authorization: Bearer <your_jwt_token>" \
  "http://localhost:8000/schemes/search?q=scholarship+engineering+Maharashtra&state=Maharashtra"
```

### 4. Admin Management Endpoints
- List unverified schemes: `GET /admin/schemes?status=unverified`
- View scheme details & version history: `GET /admin/schemes/{id}`
- Verify scheme status to `active`: `POST /admin/schemes/{id}/verify`
- Mark scheme status as `expired`: `POST /admin/schemes/{id}/mark-outdated`

---

## Run Full Pytest Suite (25 Tests)
Run unit & integration tests covering Auth, Profile, Tri-State Eligibility Engine, Crawler, Extractor, Grounding Check, Prompt-Injection Defense, Versioning, Admin API, and Hybrid RRF Retriever:
```bash
cd backend
pytest
```

---

## Deliverables Status
- [x] **Phase 1**: FastAPI core, PostgreSQL 16 + pgvector, JWT Auth, Profile CRUD, Tri-state Deterministic Eligibility Evaluator, React Frontend.
- [x] **Phase 2**: Sources allowlisting (`sources.yaml`), HTML/PDF Crawler, Structured LLM Extractor, Grounding Check, Prompt-Injection Defense, Scheme Versioning, Hybrid RRF Search, Ingestion CLI (`run.py`), Admin Verification API, Pytest Suite (25/25 passing).
