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
- [x] All endpoints return correct JSON responses
- [x] `/search` returns top-10 ranked jobs with match scores in < 5 seconds
- [x] `/crawl` kicks off background task and returns immediately
- [x] Integration test: crawl → DB → search → ranked output
- [x] OpenAPI docs render without errors

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
- [x] Dashboard fetches and displays real data from FastAPI backend
- [x] Resume input form triggers `/search` and shows ranked results
- [x] Apply links open in new tabs
- [x] UI works on mobile (responsive)
- [x] No console errors or broken states

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

### Phase 4 – FastAPI Backend *(2026-07-03)*

**Insights:**
- FastAPI's `TestClient` uses a thread pool to run sync endpoints, which caused `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. Fix: pass `check_same_thread=False` when creating test connections.
- CORS restricted to `localhost:5173` (Vite default) — frontend will be Phase 5.
- `DATABASE_PATH` env var (default `jobs.db`) worked cleanly — `api/dependencies.py` reads it at call time, but `api/routes/search.py` and `api/routes/crawl.py` have it as a module-level constant (evaluated at import time). Tests mock the downstream functions instead of fighting import order.
- Pydantic v2 models auto-generate the OpenAPI schema — `/docs` renders fully without any manual config.
- `BackgroundTasks` is sufficient for fire-and-forget crawling in MVP — no Celery/Redis needed.

**Files created:** `api/__init__.py`, `api/main.py`, `api/models.py`, `api/dependencies.py`, `api/routes/__init__.py`, `api/routes/jobs.py`, `api/routes/search.py`, `api/routes/crawl.py`, `tests/conftest.py`, `tests/test_api_jobs.py`, `tests/test_api_search.py`, `tests/test_api_crawl.py`

### Phase 5 – React Frontend *(2026-07-03)*

**Insights:**
- Vite proxy with `rewrite` is essential when the API routes don't have an `/api` prefix. Without `rewrite: (path) => path.replace(/^\/api/, "")`, the proxy forwards `/api/health` to `localhost:8000/api/health` (404). With rewrite, it becomes `localhost:8000/health` (200).
- MUI v6 + Vite + React 19 + TypeScript scaffolded cleanly. The production build produces a 137 KB gzipped JS bundle — fast enough for MVP.
- Frontend has zero unit tests (intentional — deferred to post-MVP). Manual smoke test confirmed search, crawl, and health all work via Vite proxy.
- `@mui/icons-material` was installed but unused in this iteration (no icon usage). Kept for future enhancement.

**Files created:** `frontend/` (Vite scaffold), `frontend/src/types/index.ts`, `frontend/src/api/client.ts`, `frontend/src/components/Layout.tsx`, `frontend/src/components/SearchForm.tsx`, `frontend/src/components/CrawlForm.tsx`, `frontend/src/components/JobTable.tsx`

**Files modified:** `.gitignore` (added frontend/node_modules/, frontend/dist/)

---

## Phase 6 – Location-Aware Ranking *(2026-07-03)*

**Goal:** Add preferred-location boosting to the ranking pipeline so jobs in Bangalore/Electronic City rank higher for local job seekers.

**Key Deliverables:**
- `pipeline/rank.py` — `preferred_locations` parameter, `LOCATION_BOOST = 1.5`, `_apply_location_boost()` partial-match logic
- `pipeline/search_service.py` — shared `search()` entry point for both text and file search
- `api/routes/search.py` — pass `locations` through, add `POST /search/upload`
- Frontend locations input field + file upload

**Dependencies:** Phase 5

**Completion Criteria:**
- [x] Jobs with matching locations get 1.5x score boost
- [x] Case-insensitive partial matching (e.g. "Bengaluru" matches "Electronic City, Bengaluru")
- [x] Two-endpoint design (`POST /search` for JSON, `POST /search/upload` for file)
- [x] Resume text extracted from PDF, DOCX, TXT
- [x] All original tests plus 10+ new tests pass

**Files created:** `pipeline/search_service.py`, `api/extractor.py`, `tests/test_search_service.py`, `tests/test_extractor.py`

**Files modified:** `pipeline/rank.py`, `api/models.py`, `api/routes/search.py`, `requirements.txt`, `pyproject.toml`, `frontend/src/api/client.ts`, `frontend/src/components/SearchForm.tsx`, `frontend/src/App.tsx`, `tests/test_rank.py`, `tests/test_api_search.py`

**Insights:**
- FastAPI can't mix JSON + File in one endpoint due to Content-Type conflict → two-endpoint pattern
- PyMuPDF (fitz) and python-docx handle PDF/DOCX extraction well
- Location boosting is applied after semantic scoring, not during — avoids distorting the embedding space

---

## Phase 7 – Plugin Crawler Architecture + Company Registry *(2026-07-03)*

**Goal:** Refactor standalone crawler functions into a class-based plugin architecture with an ABC, company registry, and platform class mapping.

**Key Deliverables:**
- `crawlers/base.py` — `BaseCrawler(ABC)` with `fetch_jobs()`, `from_registry()`, `platform` classvar
- `data/companies.json` — company registry with id, display name, platform, token, locations
- `crawlers/registry.py` — load/save/lookup, `build_crawlers()`, `register_crawler()`
- Refactored `GreenhouseCrawler` and `LeverCrawler` classes (backward-compatible)

**Dependencies:** Phase 6

**Completion Criteria:**
- [x] BaseCrawler ABC enforces `fetch_jobs()` on all subclasses
- [x] Standalone `fetch_jobs()` functions preserved for backward compatibility
- [x] Registry driven by `data/companies.json`
- [x] `build_crawlers()` instantiates crawlers for all enabled companies
- [x] Display name normalization (user sees "Bosch" not "boschglobalsof")
- [x] 23 new tests covering base, registry, and class methods

**Files created:** `crawlers/base.py`, `crawlers/registry.py`, `data/companies.json`, `tests/test_base_crawler.py`, `tests/test_registry.py`

**Files modified:** `crawlers/__init__.py`, `crawlers/greenhouse.py`, `crawlers/lever.py`, `tests/test_greenhouse.py`, `tests/test_lever.py`

**Insights:**
- Backward compatibility was critical — existing tests import `fetch_jobs` and `_build_job_record` directly
- Extracted `_fetch_raw_jobs()` helper so both standalone functions and class methods share the HTTP logic
- `from_registry` classmethod keeps instantiation logic near the class definition

---

## Phase 8 – Workday ATS Crawler *(2026-07-03)*

**Goal:** Add a Workday ATS crawler supporting pagination, enabling crawling for Microsoft, Deloitte, Uber, and other Workday-based career portals.

**Key Deliverables:**
- `crawlers/workday.py` — `WorkdayCrawler(BaseCrawler)` with paginated `POST` API
- `_fetch_raw_page()` + `_fetch_all_raw_jobs()` for pagination
- Added 4 Workday companies to registry (Microsoft, Deloitte, Uber, Target)

**Dependencies:** Phase 7

**Completion Criteria:**
- [x] Paginated fetching (20 jobs per page, loops until all retrieved)
- [x] Standard job record format (same as Greenhouse/Lever)
- [x] `from_registry` factory with `subdomain` defaulting to `wd1`
- [x] 10 new tests covering build_record, fetch_jobs, and class methods

**Files created:** `crawlers/workday.py`, `tests/test_workday.py`

**Files modified:** `crawlers/__init__.py`, `data/companies.json`

**Insights:**
- Workday uses a `POST` API (not GET) with JSON body — different from Greenhouse/Lever
- `externalPath` is relative → must prepend the base careers URL
- Categories are an array with `name` key (not a flat string)
- Description can be either a dict with `text` key or a plain string

---

## Phase 9 – Dispatcher + Crawl All *(2026-07-03)*

**Goal:** Build an orchestrator that runs all enabled crawlers from the registry and stores results, with a `POST /crawl/all` endpoint and frontend button.

**Key Deliverables:**
- `crawlers/dispatcher.py` — `crawl_all()` iterates over `build_crawlers()`, fetches + stores jobs
- `POST /crawl/all` + `GET /crawl/all/{task_id}` API endpoints
- Frontend "Crawl All" button with polling for results
- In-memory task-result store for MVP

**Dependencies:** Phase 7

**Completion Criteria:**
- [x] `crawl_all()` returns per-company job count summary
- [x] Crawler exceptions don't crash the entire crawl
- [x] API returns 202 immediately, pollable via GET
- [x] Frontend shows per-company results after crawl completes
- [x] 8 new tests covering dispatcher and API endpoints

**Files created:** `crawlers/dispatcher.py`, `tests/test_dispatcher.py`, `tests/test_api_crawl_all.py`

**Files modified:** `api/models.py`, `api/routes/crawl.py`, `frontend/src/types/index.ts`, `frontend/src/api/client.ts`, `frontend/src/components/CrawlForm.tsx`, `frontend/src/App.tsx`

**Insights:**
- Background task results stored in an in-memory dict (ephemeral — fine for MVP)
- Frontend polls every 3s with a 60s timeout
- Error isolation — one failing crawler doesn't block others
- Build on top of existing `POST /crawl` — doesn't break backward compatibility

---

## Phase 10 – Custom Scrapers Tier 1 *(2026-07-03)*

**Goal:** Implement 10 company-specific custom scrapers for companies with unique career portals (not behind standard ATS).

**Key Deliverables:**
- `crawlers/custom/` — directory with 10 custom scrapers
- Each scraper: `BaseCrawler` subclass with HTML parsing via BeautifulSoup
- Registered in `crawlers/__init__.py` and added to `data/companies.json`

**Companies covered:** Google, Amazon, Meta, NVIDIA, IBM, Oracle, Cisco, Intel, Qualcomm, Apple

**Dependencies:** Phase 7

**Completion Criteria:**
- [x] 10 custom crawler classes in `crawlers/custom/`
- [x] Each implements `fetch_jobs()` + `from_registry()`
- [x] All registered and added to companies.json
- [x] 37 new tests covering construction, registry factory, and fetch (mocked)
- [x] Backward compatible — all existing tests pass

**Files created:** `crawlers/custom/__init__.py`, `crawlers/custom/google_careers.py`, `crawlers/custom/amazon_careers.py`, `crawlers/custom/meta_careers.py`, `crawlers/custom/nvidia_careers.py`, `crawlers/custom/ibm_careers.py`, `crawlers/custom/oracle_careers.py`, `crawlers/custom/cisco_careers.py`, `crawlers/custom/intel_careers.py`, `crawlers/custom/qualcomm_careers.py`, `crawlers/custom/apple_careers.py`, `tests/test_custom_scrapers.py`

**Files modified:** `crawlers/__init__.py`, `data/companies.json`

**Insights:**
- Custom scrapers use a mix of HTML parsing (BeautifulSoup) and JSON-embedded data (ld+json, `__INITIAL_STATE__`)
- Each company has a unique page structure — generic selectors cover the most common patterns
- Many companies use Workday under the hood (NVIDIA, Adobe) but expose custom URLs — we still use the Workday API for those
- Mocking HTTP responses is essential for reliable testing

---

## Phase 11 – Playwright Pool *(2026-07-03)*

**Goal:** Provide a pooled Playwright browser manager for JS-heavy career pages, with graceful fallback when Playwright is not installed.

**Key Deliverables:**
- `crawlers/playwright_pool.py` — `PlaywrightPool` with max 3 concurrent browsers, semaphore-based concurrency
- `scripts/setup.ps1` — Windows PowerShell setup script (venv, deps, Playwright, DB, registry check)
- Module-level singleton via `get_pool()` / `close_pool()`

**Dependencies:** Phase 7

**Completion Criteria:**
- [x] Lazy import — Playwright not required to import the module
- [x] Returns `None` gracefully when Playwright is not installed
- [x] Semaphore limits concurrent browser usage to `max_browsers`
- [x] Singleton pattern for application-wide reuse
- [x] 7 tests covering pool lifecycle and missing-Playwright fallback
- [x] Setup script automates Windows deployment

**Files created:** `crawlers/playwright_pool.py`, `scripts/setup.ps1`, `tests/test_playwright_pool.py`

**Insights:**
- Lazy import avoids import errors when Playwright is not installed
- `asyncio.Semaphore` is the idiomatic Python approach for limiting concurrent async resource usage
- Module-level singleton pattern matches the embedding model singleton pattern
- Playwright navigation uses `"networkidle"` wait strategy for JS-rendered pages
