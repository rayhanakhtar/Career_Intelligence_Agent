# DECISIONS.md

> Log of architectural and design decisions made during development.

---

### Decision #1: Core-First Approach over Full-Stack MVP

**Decision:** Use core-first (standalone script → SQLite → embeddings → API → UI) over full-stack from day one.

**Alternatives:** Full-stack from day one (FastAPI + React + Docker + Postgres); Jupyter notebook prototype.

**Pros:** Proves concept in hours, builds ML skills early, incremental complexity, zero cost, beginner-friendly.

**Cons:** Some refactoring needed when wrapping in FastAPI later; no production-ready foundation from the start.

**Future:** Phase 4 will wrap scripts into a FastAPI service layer; the SQLite-based design makes this straightforward.

---

### Decision #2: SQLite over PostgreSQL

**Decision:** Use SQLite + FAISS for MVP rather than PostgreSQL + pgvector.

**Alternatives:** PostgreSQL + pgvector (production-grade, native vector support, but Docker/install overhead); MongoDB (NoSQL, poor fit for relational job data).

**Pros:** Zero configuration, single file, Python built-in. FAISS is faster than pgvector at small-to-medium scale. No Docker required.

**Cons:** No native vector support in SQLite (FAISS fills the gap); less scalable beyond ~100K jobs. Manual migration needed to switch.

**Future:** Migrate to Postgres + pgvector if the dataset grows beyond SQLite's practical limits. Schema is already designed with migration in mind.

---

### Decision #3: `responses` library for HTTP mocking in tests

**Decision:** Use the `responses` library to mock `requests` calls in unit tests, rather than hitting real APIs or using `unittest.mock`.

**Alternatives:** `unittest.mock.patch` (stdlib, no extra dependency but verbose); `requests-mock` (similar API, slightly less popular); VCR.py (records cassettes, heavy for unit tests).

**Pros:** Clean decorator-based API (`@responses.activate`), lightweight, captures the full request/response cycle, widely adopted, tests run offline and deterministically.

**Cons:** Extra dependency (mitigated by pinning in `requirements.txt`); only works with `requests` library (fine since that's our HTTP library).

**Future:** If we add Playwright for JS-heavy sites, Playwright tests will use Playwright's own browser-level testing — `responses` remains for `requests`-based crawlers only.

---

### Decision #4: Removed redundant `_KEYWORD_CLUES` ATS detection layer

**Decision:** Removed the low-confidence (0.3) keyword-matching layer from `ats_detector.py` after realising it was never reachable.

**Alternatives:** Keep it as a dead code path; restructure the detection to specifically scan `<meta>` tags only for the 0.7 layer.

**Pros:** Removes dead code, simpler logic (2 layers instead of 3), no hidden bugs from unreachable branches.

**Cons:** Slightly less granular confidence scoring — full HTML text check and meta-tag check now both return 0.7. Acceptable for MVP.

**Future:** If finer granularity is needed later, re-introduce keyword matching by checking only `<meta>` tags for the 0.7 layer and full body text for 0.3.

---

### Decision #5: SQLite UPSERT over INSERT OR IGNORE for dedup

**Decision:** Use `INSERT ... ON CONFLICT(company, title) DO UPDATE` (UPSERT) for handling duplicate job records, rather than `INSERT OR IGNORE` or application-level dedup.

**Alternatives:** `INSERT OR IGNORE` (silently drops duplicates, keeps stale data); `INSERT OR REPLACE` (deletes and re-inserts, loses `created_at` timestamp); application-level dedup via SELECT-then-INSERT (race condition prone, extra round-trip).

**Pros:** UPSERT preserves the original `created_at` timestamp while refreshing all other fields (location, description, posted_at, etc.). Single SQL statement, atomic, no race conditions. Crawlers can re-crawl the same company without creating noise.

**Cons:** Requires SQLite 3.24+ (available in Python 3.11+). Slightly more verbose SQL than `INSERT OR IGNORE`.

**Future:** The auto-increment integer `id` doubles as the FAISS index position in Phase 3 — no re-indexing needed when rows are UPSERTed since `id` stays stable.

---

### Decision #6: FAISSVectorStore auto-detects dimension instead of requiring it at construction

**Decision:** Removed the `dimension` parameter from `FAISSVectorStore.__init__()`. The dimension is now auto-detected from the embedding array passed to `build()`. An empty build falls back to 384 (all-MiniLM-L6-v2's default).

**Alternatives:** Keep `dimension=384` as a constructor argument; pass dimension to both `__init__` and `build()`.

**Pros:** Simplifies the API (no redundant parameter), avoids mismatches between declared and actual dimension, the dimension is inherently known from the data.

**Cons:** Empty index assumes 384 — technically brittle if a different model is used. Mitigated by the fact that we only use all-MiniLM-L6-v2 and an empty index is only used as a sentinel.

**Future:** If we support multiple embedding models, restore the `dimension` parameter or read it from a config/model registry.

---

### Decision #7: FastAPI with BackgroundTasks over Celery for async crawling

**Decision:** Use FastAPI's built-in `BackgroundTasks` for the `POST /crawl` endpoint rather than Celery or an external task queue.

**Alternatives:** Celery + Redis (production-grade, persistent queue, task status tracking); `asyncio.create_task` (runs in event loop, no thread isolation).

**Pros:** Zero infrastructure (no Redis, no worker processes), built into FastAPI, simple API (`background_tasks.add_task`), sufficient for MVP scale (<100 concurrent crawl requests).

**Cons:** No persistence (tasks lost on server restart), no task status/history tracking, no retry mechanism, tasks run in the same process (block the event loop thread pool).

**Future:** Add a `task_status` table in SQLite and a `GET /tasks/{id}` endpoint for status tracking. Migrate to Celery if crawl volume exceeds ~100 concurrent requests.

---

### Decision #8: CORS restricted to localhost:5173

**Decision:** Set `allow_origins=["http://localhost:5173"]` on the CORS middleware.

**Alternatives:** `allow_origins=["*"]` (easier for testing, security risk); no CORS (frontend won't work).

**Pros:** Secure by default — only the Vite dev server can call the API. Prevents accidental exposure in development.

**Cons:** Must add production origins before deployment. Phase 5 (React frontend) runs on port 5173 by default.

**Future:** Read `ALLOWED_ORIGINS` from env var for production deployment.

---

### Decision #9: Vite dev proxy over direct CORS calls

**Decision:** Use Vite's built-in dev server proxy (`/api` → `localhost:8000`) instead of making the frontend call `localhost:8000` directly.

**Alternatives:** Direct `fetch("http://localhost:8000/jobs")` (works, but requires CORS and exposes backend port); no proxy at all (breaks without CORS config).

**Pros:** Cleaner frontend code (`fetch("/api/jobs")`), no CORS issues in development, backend port is abstracted away, Vite handles the rewrite automatically.

**Cons:** Proxy only works in dev — production needs a real reverse proxy (nginx, or serve the built frontend from FastAPI as static files). The `/api` path prefix must be stripped via `rewrite` since the backend routes don't have an `/api` prefix.

**Future:** For production, either serve the `frontend/dist/` folder as FastAPI static files, or deploy behind nginx that handles the reverse proxy and static file serving.

---

### Decision #10: Two-endpoint design for resume search (JSON vs file upload)

**Decision:** Use separate `POST /search` (JSON body with `resume_text`) and `POST /search/upload` (multipart `resume_file`) endpoints instead of a single endpoint that accepts both.

**Alternatives:** Single endpoint with `Content-Type` switching (infeasible — FastAPI can't mix `BaseModel` and `UploadFile` in the same endpoint); base64-encode the file in JSON (wasteful, client-unfriendly).

**Pros:** Clean separation of concerns, standard REST patterns, each endpoint has a well-defined content type, no ambiguity for clients.

**Cons:** Two endpoints to document and test; clients must choose the right one based on whether they have text or a file.

---

### Decision #11: Abstract Base Class + Registry for crawler architecture

**Decision:** Refactored standalone `fetch_jobs()` functions into a class hierarchy rooted at `BaseCrawler(ABC)`, with a JSON-driven company registry and platform-to-class mapping.

**Alternatives:** Keep standalone functions (no polymorphism, harder to extend); use a decorator-based registration system (cleverer but less discoverable).

**Pros:** ABC enforces interface contract; registry provides a single source of truth for company config; `from_registry()` factory method keeps instantiation near the class; `build_crawlers()` enables "crawl all" with zero config.

**Cons:** More boilerplate than standalone functions; two APIs coexist (legacy functions + new classes) for backward compatibility.

---

### Decision #12: Display name normalization in job records

**Decision:** The class-based crawlers set `company` to the display name from the registry (e.g. "Bosch"), while the legacy standalone functions continue to use the board token (e.g. "boschglobalsof").

**Alternatives:** Change the legacy functions too (breaks backward compat); store both internal ID and display name in the DB (extra column, migration needed).

**Pros:** Users see clean company names in the UI/API; backward compat maintained for existing DB records and tests; clear separation between old and new behavior.

**Cons:** DB may contain a mix of token-based and display-name-based company values if both code paths are used.

---

### Decision #13: Workday API via POST with pagination

**Decision:** Implement the Workday crawler using the `POST /wday/cxs/{subdomain}/{tenant}/jobs` API with JSON body containing `limit`, `offset`, and `searchText`, rather than scraping the HTML career page.

**Alternatives:** Scrape the HTML career page with BeautifulSoup (fragile, JS-rendered); use Playwright (heavy, overkill for Workday's stable API).

**Pros:** Workday's REST API is well-documented, returns clean JSON, supports pagination natively, no JS rendering needed.

**Cons:** Requires knowing the tenant name and subdomain (not just a URL); uses POST instead of GET (slightly different from Greenhouse/Lever).

---

### Decision #14: Dispatcher with isolated error handling

**Decision:** In `crawl_all()`, wrap each crawler's `fetch_jobs()` call in a try/except so one failing crawler doesn't abort the entire batch.

**Alternatives:** Let exceptions propagate and fail fast (simpler, but loses results from other companies); use `asyncio.gather(return_exceptions=True)` (async rewrite needed).

**Pros:** Resilient — a single company's career page timeout doesn't block the other 20+ companies; per-company error logging.

**Cons:** Silent failures if logging is not monitored; no retry mechanism for transient failures.

---

### Decision #15: Custom scrapers with BeautifulSoup over Playwright by default

**Decision:** Implement all 10 custom scrapers using `requests` + BeautifulSoup for HTML parsing, with Playwright as a future fallback only for JS-heavy pages.

**Alternatives:** Use Playwright for all scrapers (heavy, slow, extra dependency); use raw regex parsing (brittle).

**Pros:** Fast (no browser overhead), lightweight, no extra dependency for most scrapers; BeautifulSoup handles the 80% case well; PlaywrightPool is ready for the remaining 20%.

**Cons:** Some career pages require JS rendering — those will need Playwright integration later; HTML selectors may break if the company redesigns its career portal.

---

### Decision #16: PlaywrightPool with lazy import and semaphore concurrency

**Decision:** Wrap Playwright in a pool that lazy-imports the library, uses `asyncio.Semaphore` for concurrency control (max 3 browsers), and returns `None` gracefully if Playwright is not installed.

**Alternatives:** Import Playwright eagerly (breaks the app if not installed); use `asyncio.Queue` for browser management (more complex).

**Pros:** Playwright is truly optional — the app works without it; graceful degradation; semaphore is Python-idiomatic for limiting concurrent async resource usage; singleton pattern matches the embedding model.

**Cons:** Async-only API (sync code needs `asyncio.run()`); browser instances consume ~200 MB RAM each.
