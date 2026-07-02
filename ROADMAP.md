# ROADMAP

> Phased implementation plan for the Career Intelligence Agent. This is a living document — update it as each phase completes.

---

## Phase 0 – Research & Setup *(Complexity: Low)*

**Goal:** Validate core APIs (Greenhouse, Lever) and establish the development environment.

**Key Deliverables:**
- Manual test of Greenhouse public API (`boards-api.greenhouse.io/v1/boards/{token}/jobs`) — confirm JSON structure
- Manual test of Lever public API (`api.lever.co/v0/postings/{company}`)
- Python virtual environment + `requirements.txt` with pinned dependencies
- Git repo initialized with `.gitignore`

**Dependencies:** None (starting point)

**Completion Criteria:**
- [ ] Both APIs return valid JSON for at least 2 test companies
- [ ] Environment installs cleanly from `requirements.txt`
- [ ] `pip install` runs without errors

---

## Phase 1 – MVP Crawlers *(Complexity: Medium)*

**Goal:** Write standalone Python scripts that fetch jobs from Greenhouse and Lever and save raw data to JSON/CSV.

**Key Deliverables:**
- `crawlers/greenhouse.py` — fetches all active jobs for a given board token, saves to JSON
- `crawlers/lever.py` — fetches all active jobs for a given company, saves to JSON
- `crawlers/ats_detector.py` — URL pattern matching (greenhouse.io, lever.co, workday.com, etc.)
- Shared helpers for HTTP requests, error handling, and rate limiting

**Dependencies:** Phase 0

**Completion Criteria:**
- [x] 5+ companies successfully crawled (at least 3 Greenhouse, 2 Lever)
- [x] Raw job output validated (title, location, description, apply URL present)
- [x] ATS detector correctly identifies known URL patterns
- [x] Unit tests for parser functions (mock API responses)
- [x] All HTTP errors handled gracefully (timeout, 4xx, 5xx)

---

## Phase 2 – SQLite Storage *(Complexity: Low)*

**Goal:** Replace JSON file output with a SQLite database. Design a schema, insert jobs, and deduplicate.

**Key Deliverables:**
- `database/schema.py` — SQLite schema (jobs table: id, company, title, location, description, apply_url, source, posted_at, created_at)
- `database/crud.py` — insert, select, dedup-by-(company + title) logic
- Migration: update crawlers to write to SQLite instead of JSON
- Basic query script to list stored jobs

**Dependencies:** Phase 1

**Completion Criteria:**
- [x] Schema enforces deduplication (UNIQUE constraint on company + title)
- [x] Repeated crawl of same company does not create duplicate rows
- [x] CRUD functions have unit tests with in-memory SQLite
- [x] All jobs from Phase 1 imported into DB without data loss

---

## Phase 3 – Semantic Layer *(Complexity: High)*

**Goal:** Embed job descriptions using `sentence-transformers` (all-MiniLM-L6-v2), build a FAISS index, compute cosine similarity against a resume/profile, and return ranked results.

**Key Deliverables:**
- `embeddings/embedder.py` — loads model, generates 384-dim embeddings for text
- `embeddings/matcher.py` — cosine similarity scoring between resume and job descriptions
- `embeddings/vector_store.py` — FAISS index build, save, load, and nearest-neighbor search
- `pipeline/rank.py` — combines similarity scores, filters, and returns top-N ranked jobs
- Script to ingest a resume text file and print ranked matches

**Dependencies:** Phase 2

**Completion Criteria:**
- [x] Model loads and embeds 100 job descriptions in under 30 seconds on CPU
- [x] FAISS index correctly returns nearest neighbors (spot-check with known similar text)
- [x] Resume matching produces plausible scores (manual review of top-5)
- [x] Unit tests for embedder, matcher, and rank functions
- [x] No cloud APIs used — all inference is local

---

## Phase 4 – FastAPI Backend *(Complexity: Medium)*

**Goal:** Wrap the pipeline (crawl → store → embed → rank) in a FastAPI application with documented endpoints.

**Key Deliverables:**
- `api/main.py` — FastAPI app entry point
- `api/routes/jobs.py` — `GET /jobs` (list all), `GET /jobs/{id}` (detail)
- `api/routes/search.py` — `POST /search` (resume text in, ranked jobs out)
- `api/routes/crawl.py` — `POST /crawl` (trigger crawl for a given company)
- Background task runner for async crawling
- Auto-generated OpenAPI docs at `/docs`

**Dependencies:** Phase 3

**Completion Criteria:**
- [ ] All endpoints return correct JSON responses
- [ ] `/search` returns top-10 ranked jobs with match scores in < 5 seconds
- [ ] `/crawl` kicks off background task and returns immediately
- [ ] Integration test: crawl → DB → search → ranked output
- [ ] OpenAPI docs render without errors

---

## Phase 5 – React Frontend *(Complexity: Medium)*

**Goal:** Build a clean React (Vite + MUI) dashboard that displays ranked jobs and lets the user submit their resume text.

**Key Deliverables:**
- `frontend/` — Vite + React project scaffold
- Job table component with columns: match %, company, role, location, apply link
- Resume input form (textarea or file upload)
- Search/Crawl trigger buttons
- Loading states and error handling

**Dependencies:** Phase 4

**Completion Criteria:**
- [ ] Dashboard fetches and displays real data from FastAPI backend
- [ ] Resume input form triggers `/search` and shows ranked results
- [ ] Apply links open in new tabs
- [ ] UI works on mobile (responsive)
- [ ] No console errors or broken states

---

## Completed

### Phase 1 – MVP Crawlers *(2026-07-02)*

**Insights:**
- Greenhouse API (`boards-api.greenhouse.io`) works reliably with no auth needed. Board token is the key variable.
- Lever API (`api.lever.co/v0/postings/{company}?mode=json`) has inconsistent company slug naming. Some companies return empty/404 — handled gracefully.
- ATS detection via URL patterns alone covers ~80% of cases. Two-layer cascade (URL → HTML) proved sufficient for Phase 1.
- `responses` library makes HTTP mocking clean and deterministic for unit tests.
- The `_KEYWORD_CLUES` layer was removed as redundant — all entries overlapped with `_META_CLUES` when checking full page HTML.

**Files created:** `crawlers/__init__.py`, `crawlers/ats_detector.py`, `crawlers/utils.py`, `crawlers/greenhouse.py`, `crawlers/lever.py`, `tests/test_ats_detector.py`, `tests/test_utils.py`, `tests/test_greenhouse.py`, `tests/test_lever.py`, `data/sample_resume.txt`, `data/sample_greenhouse.json`, `.gitignore`, `requirements.txt`

### Phase 2 – SQLite Storage *(2026-07-03)*

**Insights:**
- SQLite `ON CONFLICT DO UPDATE` (UPSERT) is cleaner than `INSERT OR IGNORE` — preserves `created_at` while refreshing other fields.
- In-memory SQLite (`:memory:`) is lightweight and fast for unit tests; no file cleanup needed.
- Auto-increment integer `id` doubles as a natural FAISS index position (prep for Phase 3).
- Using `python -m database.import` (not `python database/import.py`) ensures package imports resolve correctly.

**Files created:** `database/__init__.py`, `database/schema.py`, `database/crud.py`, `database/import.py`, `tests/test_crud.py`

### Phase 3 – Semantic Layer *(2026-07-03)*

**Insights:**
- After the FAISSVectorStore was refactored to auto-detect dimension from data in `build()`, all call sites (both production and test) needed to stop passing `dimension=384` to the constructor.
- The sentence-transformers model (`all-MiniLM-L6-v2`) loads once per process via a module-level singleton — the first `embed()` call is slow (~12s download/unpack), but subsequent calls are fast.
- FAISS `IndexFlatIP` with pre-normalized vectors gives the same results as cosine similarity, avoiding an extra L2 normalization step at search time.
- Full pipeline (21 jobs: load → embed → index → search → score → format) runs in ~500ms after model is cached.

**Files created:** `embeddings/__init__.py`, `embeddings/embedder.py`, `embeddings/vector_store.py`, `embeddings/matcher.py`, `pipeline/__init__.py`, `pipeline/rank.py`, `tests/test_embedder.py`, `tests/test_vector_store.py`, `tests/test_rank.py`
