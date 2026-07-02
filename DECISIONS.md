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
