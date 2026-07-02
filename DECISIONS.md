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
