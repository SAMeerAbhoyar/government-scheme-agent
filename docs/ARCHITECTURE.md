# Architecture & System Design Document

## 1. System Overview & Core Principles

The **Automated Government Scheme Recommendation Agent** is a multi-tier platform built to ingest government schemes from official sources (focusing on Central + Maharashtra schemes), normalize eligibility criteria into structured rules, match citizen demographic profiles against these rules deterministically, and explain match reasons backed by direct source citations.

### Strict Architectural Principles
1. **Single Backend Framework**: FastAPI (Python 3.11+) handles all REST API endpoints. Node.js or Express are strictly disallowed.
2. **Frontend Architecture**: Single Page Application built with React, Vite, Tailwind CSS, and React Router v6.
3. **Database Architecture**: PostgreSQL 16 equipped with `pgvector` (`pgvector/pgvector:pg16`).
4. **ORM & Migrations**: SQLAlchemy 2.0 (async via `asyncpg`) for database access and Alembic for schema migrations. Pydantic v2 is used exclusively for payload and domain model validation.
5. **Authentication & Authorization**: Stateless JWT Bearer tokens with `bcrypt` password hashing. RBAC supporting `user` and `admin` roles.
6. **Offline Ingestion Rule**: Web scraping, PDF extraction, and LLM extractions occur **strictly offline** as scheduled or CLI jobs. Request paths MUST NEVER invoke crawlers or external scraping.
7. **Domain Allowlisting & Security**: Crawlers strictly enforce domain allowlists (`.gov.in`, `.nic.in`, `maharashtra.gov.in`, `myscheme.gov.in`, `scholarships.gov.in`).
8. **Prompt-Injection Defense**: Extracted text is isolated as untrusted data. Prompts explicitly instruct LLMs to ignore embedded instructions and forbid tool invocation.
9. **Grounding Verification**: Every leaf eligibility rule must contain a literal `source_quote` substring verified against raw document text before approval.
10. **Deterministic Eligibility Rule Engine**: Scheme eligibility criteria matching is performed using **100% deterministic code** (`RuleGroup` & `RuleLeaf` evaluator). LLMs are strictly excluded from the core decision boundary.
11. **Hybrid RAG Retrieval with RRF**: Searches merge PostgreSQL Full-Text Search (`tsvector`) and `pgvector` Cosine Similarity using Reciprocal Rank Fusion ($RRF\_Score = \frac{1}{60 + rank_{fts}} + \frac{1}{60 + rank_{vec}}$).

---

## 2. Component Design & System Architecture

```
+-----------------------------------------------------------------------+
|                    OFFLINE INGESTION & PIPELINE                       |
|   (CLI python -m app.ingestion.run / APScheduler Daily Cron Job)       |
|                                                                       |
|  [ sources.yaml ] ---> ( Crawler ) ---> [ Grounding & Hash Check ]    |
|                             |                                         |
|                             v                                         |
|                      ( Extractor LLM ) ---> [ Pydantic Rule Tree ]    |
|                             |                                         |
|                             v                                         |
|                      ( Upsert & Versioning )                          |
+-----------------------------------+-----------------------------------+
                                    | SQLAlchemy 2.0
                                    v
+-----------------------------------------------------------------------+
|                             DATABASE                                  |
|                   PostgreSQL 16 + pgvector                            |
|  10 Relational Tables + GIN Index on Full-Text Search (tsvector)       |
+-----------------------------------+-----------------------------------+
                                    ^
                                    | Hybrid RRF Retrieval & Rule Checks
+-----------------------------------+-----------------------------------+
|                        BACKEND & AGENTS (FastAPI)                     |
|                                                                       |
|  +-------------------+  +-------------------+  +-------------------+  |
|  | Deterministic     |  | Discovery Router  |  | Guardrailed       |  |
|  | Matcher Engine    |  | Mode 1 & Mode 2   |  | Explainer Agent   |  |
|  | (matching.py)     |  | (discovery.py)    |  | (explainer.py)    |  |
|  +-------------------+  +-------------------+  +-------------------+  |
|  | Questions Service |  | User Features     |  | Evaluation        |  |
|  | (questions.py)    |  | Bookmarks/Compare |  | Harness (eval/)   |  |
|  +-------------------+  +-------------------+  +-------------------+  |
+-----------------------------------+-----------------------------------+
                                    ^
                                    | HTTP / REST (JWT Auth)
+-----------------------------------+-----------------------------------+
|                              FRONTEND                                 |
|         React + Vite + Tailwind CSS + React Router v6                 |
|  - Dashboard (Mode 1 & Mode 2)      - Saved Bookmarks                 |
|  - Inline Missing-Info Questions    - Activity History                |
|  - Side-by-Side Compare Matrix      - Scheme Detail & Feedback        |
+-----------------------------------------------------------------------+
```

---

## 3. Phase 3 Recommendation Engine & Discovery Pipelines

1. **Deterministic Matching Engine (`services/matching.py`)**:
   - Compares user demographic profile against scheme `RuleGroup` AST.
   - Statuses: `potentially_relevant` (100% pass), `cannot_determine` (no fails, missing fields), `not_matching` (any required rule fail).
   - Priority Ranking: Status > Verification > Missing Fields Count > Deadline.

2. **Both Discovery Modes (`api/discovery.py`)**:
   - **Mode 1 (User Query)**: `POST /discover/query` parses natural language query via `QueryPlannerAgent`, performs Hybrid RAG retrieval, then evaluates matching engine.
   - **Mode 2 (AI Profile Discovery)**: `POST /discover/profile` evaluates all active schemes directly against citizen profile.

3. **Guardrailed Explainer (`agents/explainer.py`)**:
   - Verifies every numeric/date value in generated text against structured `MatchResult`.
   - On hallucination detection, discards LLM output and falls back to deterministic markdown template.
   - Appends mandatory legal disclaimer to all output.

4. **Offline Evaluation Harness (`backend/eval/run.py`)**:
   - Benchmark measuring Precision@5, Eligibility Accuracy, and Latency against 5 citizen personas. Results published to `docs/EVALUATION_RESULTS.md`.

---

## 3. Database Schema Specification (10 Tables)

- **`users`**: User identities, authentication records, roles (`user`, `admin`), and explicit consent timestamp.
- **`profiles`**: User demographic profiles. All fields are nullable (`null` maps to "unknown"). Includes demographics, education, financial, and social categories.
- **`schemes`**: Ingested government schemes with department info, JSONB eligibility rules, required documents, and URLs.
- **`scheme_versions`**: Audit log of scheme modifications and raw JSON snapshots.
- **`scheme_chunks`**: Document chunks for hybrid retrieval (Vector embedding `vector(768)` + `tsvector` for keyword search).
- **`saved_schemes`**: User saved bookmark associations.
- **`search_history`**: History of user search queries and intent classifications.
- **`recommendations`**: Stored recommendation outputs, match status (`match`, `no_match`, `partial`), and rationale.
- **`source_records`**: Provenance tracking for raw government web pages and PDFs.
- **`feedback`**: User feedback ratings and comments on match accuracy.

---

## 4. Eligibility Engine Architecture

Eligibility rules are modeled as hierarchical trees:
- **`RuleLeaf`**: A single condition on a citizen attribute (e.g., `age >= 18`, `social_category in ['SC', 'ST']`, `annual_income <= 250000`).
- **`RuleGroup`**: Logical combination node (`all_of` [AND], `any_of` [OR], `not_of` [NOT]).

### Tri-State Evaluation Logic:
- `MATCH`: All required conditions are verified satisfied.
- `NO_MATCH`: At least one condition is verified violated.
- `UNKNOWN`: Insufficient citizen profile data to make a definitive decision.

---

## 5. Security & Data Protection
- Secrets and keys are managed solely through environment variables (`.env`).
- User passwords are strictly hashed with `bcrypt` (work factor >= 12).
- Sensitive demographic fields support explicit "prefer not to say" selections, which store `null` to ensure privacy and trigger `UNKNOWN` tri-state evaluations.
- Full account deletion (`DELETE /account`) guarantees complete cascade deletion of all user data, profiles, recommendations, and search history.
