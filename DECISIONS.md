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
