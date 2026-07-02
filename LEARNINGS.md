# LEARNINGS.md

> Technical insights and lessons learned during development.

---

*Issue:* Why use cosine similarity on embeddings for matching instead of keyword filtering?

*Learning:* Embeddings (like `all-MiniLM-L6-v2`) convert text to dense vectors (384-dim). Cosine similarity compares these vectors so that semantically similar texts (e.g. *"AI Engineer"* vs *"Machine Learning Engineer"*) align closely even when they share zero exact keywords. Keyword filters (regex, tf-idf) would miss this relationship entirely. Cosine similarity is also fast — a single dot product over 384 floats is microseconds. This is the standard approach for sentence-level semantic search.

*Next:* Test if L2 (Euclidean) distance or inner product yields different rankings for our specific job description dataset. Also test whether normalizing vectors before indexing changes match quality.

---

*Issue:* How to detect which ATS a company uses from its career page URL?

*Learning:* Most ATS platforms leave obvious fingerprints in their URL structure. Greenhouse uses `boards.greenhouse.io/{token}`, Lever uses `jobs.lever.co/{company}`, Workday uses `myworkdayjobs.com` or `{company}.wd1.myworkdayjobs.com`. Simple substring/pattern matching on the URL catches ~80% of cases instantly. No need to fetch the page or parse HTML for detection — a lightweight dictionary lookup is sufficient. The remaining ~20% (custom career pages, unknown ATS) require fetching the page and looking for telltale HTML markers or fall back to generic scraping.

*Next:* Build `ats_detector.py` with a pattern dictionary and confidence scoring (e.g. URL match = high confidence, HTML meta-tag match = medium). Also compile a list of known company career URLs for Electronic City to test against.

---

*Issue:* Why store job data in SQLite and vectors in FAISS instead of using pgvector from the start?

*Learning:* SQLite + FAISS is a hybrid that hits the sweet spot for an MVP. SQLite handles structured data (company, title, location, apply URL) with zero config and familiar SQL queries. FAISS handles vector search independently and, at our scale (<10K jobs), is actually faster than pgvector because there's no database connection overhead. The two are loosely coupled via a shared job ID — FAISS stores `[job_id, embedding]` pairs, SQLite stores the metadata. Migration to Postgres + pgvector later means exporting SQLite rows and rebuilding the FAISS index in pgvector's format — both are well-understood operations.

*Next:* Design the SQLite schema with an integer `id` that doubles as the FAISS index position, keeping the two stores in sync trivially.

---

*Issue:* The ATS detector's keyword-matching layer (confidence 0.3) was never triggered during testing.

*Learning:* The `_KEYWORD_CLUES` dictionary contained the same entries as `_META_CLUES` ("greenhouse", "lever", "workday"). Since the detector checks the full `page_html.lower()` for both layers and `_META_CLUES` is checked first, the 0.3 layer was unreachable. URL → meta-tag → no-match was the only possible path. The entire `_KEYWORD_CLUES` layer was dead code. Removed it, reducing to a clean 2-layer cascade.

*Next:* If finer granularity is needed, restructure meta-tag detection to scan only `<meta>` tags (via BeautifulSoup) and body-text detection for the 0.3 layer. Not needed for MVP.

---

*Issue:* The Lever API returns 404 for many common company names.

*Learning:* Lever's public API (`api.lever.co/v0/postings/{company}?mode=json`) uses company slugs that don't always match the company's brand name. For example, "google", "dropbox", and "segment" all returned 404. The "lever" test company returned an empty array, confirming the endpoint works. A company's actual Lever slug must be verified manually or discovered from its career page URL (`jobs.lever.co/{slug}`).

*Next:* When building the company discovery module, extract the Lever slug from each company's career page URL rather than guessing it. The `ats_detector.py` module already extracts the slug pattern from URLs.

---

*Issue:* Should we use `INSERT OR IGNORE`, `INSERT OR REPLACE`, or `ON CONFLICT DO UPDATE` for handling duplicate job rows?

*Learning:* `ON CONFLICT(company, title) DO UPDATE` (UPSERT) is the best choice for our use case. `INSERT OR IGNORE` silently drops duplicates, leaving stale data in place. `INSERT OR REPLACE` deletes and re-inserts, which resets the auto-increment `id` and loses the `created_at` timestamp. UPSERT preserves `created_at` while refreshing all other fields — exactly what we want when re-crawling a company's career page. The auto-increment `id` stays stable, which is critical for Phase 3's FAISS integration where `id` doubles as the vector index position.

*Next:* Implement a `fetch_and_store(db_path, board_token)` function in the crawlers that calls `insert_job()` directly, skipping the JSON file intermediary. This allows both pipelines to coexist — JSON for debugging, SQLite for persistence.

---

*Issue:* Should `FAISSVectorStore` accept the embedding dimension in `__init__` or auto-detect it?

*Learning:* Auto-detecting the dimension from data in `build()` is simpler and less error-prone. When we had `FAISSVectorStore(dimension=384)`, both the tests and `pipeline/rank.py` needed to pass this parameter. After refactoring `__init__` to take no arguments and `build()` to call `embeddings.shape[1]`, we had to update 10 test call sites and 1 production call site that still passed `dimension=384`. The root cause was a disconnect between `__init__` (which stored `dimension` redundantly) and `build()` (which also set `self.dimension`). The fix: remove the constructor parameter, let `build()` always derive dimension from data.

*Next:* If we ever add a `dimension` validation or config system, consider reading it from a `ModelConfig` dataclass rather than re-introducing it to `__init__`.

---

*Issue:* Why does `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread` occur in FastAPI tests?

*Learning:* FastAPI's `TestClient` runs sync endpoint functions in a thread pool via `anyio.to_thread.run_sync`. When the test creates a `sqlite3.Connection` in the main thread and passes it to the endpoint (via dependency override), the endpoint runs in a different thread. SQLite connections default to `check_same_thread=True`, which raises `ProgrammingError` when the connection is used from a different thread. The fix: pass `check_same_thread=False` when creating the connection in test fixtures. This is safe because we never share connections across threads concurrently.

*Next:* Consider using a connection pool or creating connections per-request in the real `get_db` dependency (it already does this). The issue only applies to test dependency overrides where a pre-created connection is injected. For production, `sqlite3.connect()` in `get_db()` creates a fresh connection per request in the same thread the endpoint runs in, so the problem doesn't arise.
