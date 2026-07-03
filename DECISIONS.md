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
