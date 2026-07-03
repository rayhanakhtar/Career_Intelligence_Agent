# Career Intelligence Agent

*An AI-driven pipeline that automatically discovers, crawls, and semantically matches local AI/ML internships and entry-level jobs — starting with Electronic City, Bengaluru.*

## Problem

- **Hyper-local job search is broken.** You're an AI/ML intern in Electronic City, Bengaluru. Bosch, Infosys, Wipro, and a dozen other tech campuses are within 5 km. But finding their internship postings means checking 15+ separate career pages every week.
- **General portals make it worse.** LinkedIn, Indeed, and Naukri show duplicates, stale listings, and irrelevant senior roles.
- **No local aggregator exists.** Each company uses a different ATS (Greenhouse, Lever, Workday, etc.). There's no single place that watches them all for you.

## Solution

A lightweight, zero-cost agent that automates the entire pipeline:

1. **Crawls** 19+ company career pages across 4 platforms (Greenhouse, Lever, Workday, custom scrapers).
2. **Embeds** job descriptions using `sentence-transformers` (all-MiniLM-L6-v2) and computes cosine similarity against your resume/profile.
3. **Ranks & displays** results with match scores, location-aware boosting, and a React dashboard.

**Semantic search, not brittle keyword matching.** We embed both resumes and job descriptions into 384-dim vectors so that *"Machine Learning Engineer"* semantically matches *"Deep Learning Engineer"* even if exact keywords differ.

## Features

- **19+ Company Crawlers** — Greenhouse, Lever, Workday, and 10 custom scrapers (Google, Amazon, Meta, NVIDIA, IBM, Oracle, Cisco, Intel, Qualcomm, Apple).
- **ATS Detector** — Pattern-matches URLs to identify 9 platforms (Greenhouse, Lever, Workday, SmartRecruiters, Ashby, BambooHR, iCIMS, Taleo, Jobvite).
- **Decoupled CrawlService** — Reusable by REST API, APScheduler, or CLI (`crawlers/service.py`).
- **Company Registry** — YAML-based (`data/companies.yml`) with `renderer` field (requests/playwright), fallback JSON support.
- **FastAPI Backend** — REST endpoints for crawl, search, and job listing with auto-docs at `/docs`.
- **Persistent FAISS Index** — Cached to disk, auto-rebuilt when jobs change.
- **Paginated Job Listings** — `GET /jobs?page=&per_page=&company=&location=&source=` with filtering.
- **Resume Upload** — PDF, DOCX, and TXT via `POST /search/upload`.
- **Location-Aware Ranking** — 1.5x boost for jobs matching preferred locations.
- **React Frontend** — Vite + MUI dashboard with crawl controls and results display.
- **SQLite Persistence** — Zero-setup local database.

## Technology Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Rich ML/scraping ecosystem |
| Database | SQLite (built-in `sqlite3`) | Zero setup, single file |
| Embeddings | `sentence-transformers` + `all-MiniLM-L6-v2` | 384-dim, fast on CPU, zero cost |
| Vector Search | FAISS (CPU) | Open-source, persistent index |
| Scraping | `requests` + `BeautifulSoup` | Lightweight, capable for 90% of sites. Playwright available for JS-heavy pages |
| API Layer | FastAPI | Async, auto-docs, dependency injection |
| Frontend | React (Vite) + MUI | Modern component-based UI |
| Config | `.env` + `companies.yml` | Environment variables + YAML registry |

## Architecture

```
                     ┌──────────────┐
                     │  companies   │
                     │   .yml       │
                     └──────┬───────┘
                            ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  CrawlService│ ──▶ │  Crawler     │ ──▶ │  SQLite DB   │
│  (FastAPI /  │     │  Instances   │     │  (jobs.db)   │
│   Scheduler) │     └──────────────┘     └──────┬──────┘
└─────────────┘                                   ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  React       │ ◀── │  FastAPI     │ ◀── │  FAISS       │
│  Frontend    │     │  /search     │     │  Index       │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Setup

### Prerequisites

- Python 3.11+

### Installation

```bash
git clone https://github.com/yourusername/Career_Intelligence_Agent.git
cd Career_Intelligence_Agent

python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `jobs.db` | Path to SQLite database |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `COMPANIES_PATH` | `data/companies.yml` | Company registry path |
| `LOG_LEVEL` | `INFO` | Logging level |
| `FAISS_INDEX_DIR` | `faiss_index` | Persistent FAISS index directory |

**No API keys required.** All crawlers use public APIs or public HTML.

### Running

```bash
# Start the FastAPI server
uvicorn api.main:app --reload

# In another terminal, crawl all companies
curl -X POST http://localhost:8000/crawl/all

# Crawl a single company
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"company_id": "google"}'

# Search jobs
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "I am an AI/ML intern...", "top_k": 10}'

# List jobs with pagination
curl "http://localhost:8000/jobs?page=1&per_page=20&company=google"
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI is served at `http://localhost:5173` and connects to the FastAPI backend at `http://localhost:8000`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/crawl` | Crawl a single company by `company_id` |
| `POST` | `/crawl/all` | Crawl all enabled companies |
| `GET` | `/crawl/all/{task_id}` | Poll crawl-all results |
| `GET` | `/jobs` | List jobs with `page`, `per_page`, `company`, `location`, `source` filters |
| `GET` | `/jobs/{id}` | Get single job by ID |
| `POST` | `/search` | Semantic search with resume text |
| `POST` | `/search/upload` | Semantic search with uploaded resume file |

## Adding a New Company

1. Investigate the company's career page to determine ATS platform and API endpoints.
2. Add an entry to `data/companies.yml` with the appropriate `platform`, `renderer`, and platform-specific identifiers.
3. If the platform already has a registered crawler class, it will be picked up automatically.
4. If a new platform is needed, create a crawler class inheriting from `BaseCrawler`, implement `fetch_jobs()` and `from_registry()`, then register it in `crawlers/__init__.py`.

## Project Structure

```
├── api/                  # FastAPI application
│   ├── main.py           # Entry point, CORS, logging
│   ├── models.py         # Pydantic request/response schemas
│   ├── dependencies.py   # DB connection dependency
│   ├── routes/           # API route handlers
│   └── extractor.py      # Resume text extraction (PDF/DOCX/TXT)
├── crawlers/             # Job board crawlers
│   ├── service.py        # CrawlService orchestrator
│   ├── base.py           # BaseCrawler ABC
│   ├── registry.py       # Company registry (YAML + JSON)
│   ├── greenhouse.py     # Greenhouse ATS crawler
│   ├── lever.py          # Lever ATS crawler
│   ├── workday.py        # Workday ATS crawler
│   ├── custom/           # 10 custom company scrapers
│   ├── ats_detector.py   # ATS platform detection
│   ├── utils.py          # HTTP retry utilities
│   └── playwright_pool.py # Playwright browser pool
├── data/
│   ├── companies.yml     # Company registry (YAML)
│   └── companies.json    # Legacy JSON registry (fallback)
├── database/
│   ├── schema.py         # Table definitions
│   └── crud.py           # Insert/query operations
├── embeddings/
│   ├── embedder.py       # Sentence embedding
│   ├── vector_store.py   # FAISS index wrapper
│   └── matcher.py        # Score computation
├── pipeline/
│   ├── rank.py           # Ranking pipeline (with FAISS caching)
│   └── search_service.py # Search service wrapper
├── frontend/             # React + Vite + MUI
├── tests/                # 178+ tests (pytest)
├── .env.example          # Environment variable template
├── requirements.txt
└── README.md
```

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for detailed milestones.

## Contributing

Contributions, issues, and feature suggestions are welcome. The project is structured as independent modular agents, making it easy to extend or swap components.
