# AGENT.md — AI Career Intelligence Agent

*“This file defines permanent execution behavior. You must follow it for every task without requiring re-instruction.”
---

## Project Mission

The sole mission of this project is to **automate the discovery and ranking of local AI/ML internships and entry-level jobs** in a specific geographic area (starting with Electronic City, Bengaluru). Every module, function, and decision must serve this goal. Do not drift into generic job scraping, broad crawling utilities, or unrelated ML experiments. If a task does not directly advance this mission, flag it before proceeding.

## Tech Stack Rules

### Allowed (whitelisted)

**Phases 0–3 (MVP Core):**
- Python 3.11+
- SQLite (built-in `sqlite3`)
- `requests`
- `BeautifulSoup4` / `lxml`
- `sentence-transformers` (model: `all-MiniLM-L6-v2`)
- `FAISS` (CPU version)
- `pytest`

**Phase 4+:**
- FastAPI + Uvicorn
- React (Vite) + MUI
- `python-telegram-bot`
- Playwright or Crawl4AI (only when a target site requires JS rendering)

### Strictly Forbidden (until Phase 4+)

- PostgreSQL, Redis, Docker — use SQLite only
- Any cloud API (OpenAI, Google Vertex, Cohere, Pinecone, etc.)
- Paid LLM services of any kind
- Heavy ML models (anything larger than ~500MB or requiring a GPU)
- Scrapy / Selenium — use `requests` + `BeautifulSoup`; if JS is needed, use Playwright or Crawl4AI
- React, FastAPI, or any web framework until Phase 4

### Justification for each allowed library

| Tool | Why it was chosen |
|------|-------------------|
| SQLite | Zero setup, single file, Python built-in. Migrates to Postgres later if needed. |
| `all-MiniLM-L6-v2` | 384-dim, runs on CPU in milliseconds, top of the MTEB leaderboard for its size class. |
| FAISS | Open-source, CPU-native, handles millions of vectors. No cloud dependency. |
| `requests` + `BeautifulSoup` | Lightweight, sufficient for 90% of target sites. |

## Development Philosophy

- **No spaghetti code.** Every module has a single responsibility. No file exceeds 500 lines.
- **No mixing business logic with I/O.** Keep scraping, parsing, embedding, and ranking in separate modules. A crawler never calls an embedding model. A ranking function never makes an HTTP request.
- **Compose, don't inherit.** Use composition over class inheritance. Prefer stateless functions over objects with mutable state.
- **Fail fast, fail visibly.** Never silently swallow exceptions. Log all errors with context. If a crawl fails, log it and continue — do not halt the pipeline.
- **Keep it local.** The entire MVP must run offline or against free public APIs. Zero cloud spend.
- **Think in phases.** For each new feature, write small standalone Python scripts or functions and unit tests first. Build and test a Greenhouse API fetcher *before* integrating it into the pipeline. Verify correctness with simple examples before moving on.
- **Refactor, don't duplicate.** If code similar to an existing function is needed, refactor or import it instead of copy-pasting.

## Coding Standards

- **Style:** PEP-8 enforced. Line length 100 characters.
- **Type hints:** Required on all function signatures and dataclass fields.
- **Data models:** Use `dataclasses` or Pydantic `BaseModel` for all structured data. Never use plain dicts for business objects.
- **Docstrings:** Every module, class, and public function must have a Google-style docstring describing purpose, args, and returns.
- **Naming:** Descriptive names. `extract_jobs_from_greenhouse()` not `gh_extract()`. `normalize_experience_level()` not `norm_exp()`.
- **Logging:** Use Python's `logging` module with module-level loggers. Never `print()` for diagnostics.
- **Error handling:** Every network call must handle timeouts, HTTP errors, and malformed responses. Use retry decorators for transient failures (max 3 retries, exponential backoff).
- **No quick hacks.** No commented-out debug code, no `# TODO` left behind, no dead code. Write clean, readable code.

## File Organization

Follow this multi-agent folder structure. Each file/class does one thing.

```
project/
├── agents/          # Orchestration / pipeline agents
├── crawlers/        # ATS-specific crawlers (greenhouse.py, lever.py, ats_detector.py)
├── database/        # Schema, CRUD, migration helpers
├── embeddings/      # Embedder, matcher, vector store (FAISS)
├── pipeline/        # Ranker, filter, scoring logic
├── api/             # FastAPI routes (Phase 4+)
├── frontend/        # React app (Phase 5+)
├── tests/           # Unit + integration tests (mirrors source structure)
├── data/            # Sample job JSON, resume text for testing
├── AGENT.md
├── ROADMAP.md
├── DECISIONS.md
├── ARCHITECTURE.md
└── README.md
```

## Execution Rules

1. **Always implement and test in isolation first.** Before wiring up a full pipeline, write and verify a standalone script for one input (e.g. one Greenhouse board, one resume file).
2. **Generalize only after the single case works.** Never abstract prematurely. The ATS detector should be prototyped on one URL pattern before supporting ten.
3. **One phase at a time.** Do not skip ahead. Complete Phase 1 before touching Phase 2.
4. **Commit or checkpoint after each working sub-step.** If the user leaves, a future session should pick up from a known working state.
5. **Think like a senior dev: plan, then code.**

## Semantic-First Rule (Non-Negotiable)

- **Use embedding similarity for matching before any LLM-based reasoning.** LLMs, if introduced, are for explanation only (e.g. generating a summary of *why* a job matches).
- Use simple cosine similarity on vectors instead of keyword matching or regex filters for relevance scoring.
- The embedding + FAISS pipeline is the core "AI" of this project. Do not replace it with brittle rule-based systems or paid LLM classifiers.

## Testing

- **Unit tests:** Every new function must have a corresponding unit test using `pytest`. Mock all network calls.
- **Integration tests:** Each phase must have at least one end-to-end test (e.g. "fetch real Greenhouse jobs, store in SQLite, run embedding, return ranked results").
- **Fixtures:** Use `pytest.fixtures` for shared test data (sample job JSON, sample resume text).
- **Coverage target:** No untested code should be merged. If an edge case cannot be tested, document why in a comment.
- **Test command:** `pytest tests/ -v` must pass before any work is considered done.

## Documentation

The following files must **always** reflect the current state of the project. Update them immediately after completing any feature.

| File | Purpose |
|------|---------|
| `README.md` | Public-facing: problem, solution, features, setup, sample output. Keep succinct and recruiter-friendly. |
| `ROADMAP.md` | Tracks completed vs. planned milestones. Check off items as they are done. |
| `DECISIONS.md` | Internal decision log. |
| `ARCHITECTURE.md` | High-level design, module relationships, data flow. |

**Never let these files fall out of sync.** If code changes, docs change with it.

**Every new module must start with a brief comment describing its purpose.**

## Decision Logging

After each **architectural decision** (and at minimum after every completed phase), add an entry to `DECISIONS.md` with this template:

```markdown
## [YYYY-MM-DD] Decision: [title]

**Context:** What problem or question prompted this decision.

**Options considered:** List 2-3 alternatives with brief pros/cons.

**Rationale:** Why the chosen option won.

**Future implications:** What this decision enables or constrains later.
```

## Definition of Done

A task is complete only when **all** of these are true:

- [ ] Code is written and follows all standards above (typed, documented, logged).
- [ ] New module starts with a brief comment describing its purpose.
- [ ] Unit tests pass and cover the new functionality.
- [ ] Integration test confirms it works end-to-end.
- [ ] Type hints are present and correct.
- [ ] Docstrings are written for every public function/class.
- [ ] No `# TODO`, `# FIXME`, `print()`, or dead code remains.
- [ ] `README.md`, `ROADMAP.md`, `DECISIONS.md` (and `ARCHITECTURE.md` if needed) are updated.
- [ ] The module is composable — it can be imported and used independently.
- [ ] No overlapping or duplicate code exists — refactored if needed.

Self-check this list before declaring a task done.

## AI Behavior Checklist

Before every coding task, the agent must:

1. **Re-read** `README.md`, `AGENT.md`, `ROADMAP.md`, `DECISIONS.md`, and `ARCHITECTURE.md` (if it exists) to re-establish context.
2. **Confirm** exactly which phase and task we are on from `ROADMAP.md`.
3. **Verify** no overlapping or duplicate work exists (check existing modules and open tasks).
4. **Plan** the change in writing before opening a single file. If the change is non-trivial, describe the plan to the user for approval.
5. **Ask for clarification** if requirements are ambiguous.
6. **Never break existing code.** If a refactor is necessary, isolate it in a separate step and verify nothing regresses.
7. **Do not suggest changes to the core design unless the current design actively blocks progress.** The MVP has a defined scope — gold-plating is out of scope.

> *"Think like a senior dev: plan, then code."*
