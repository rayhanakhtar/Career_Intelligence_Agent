# Career_Intelligence_Agent

*An AI-driven pipeline that automatically discovers, crawls, and semantically matches local AI/ML internships and entry-level jobs — starting with Electronic City, Bengaluru.*

## Problem

- **Hyper-local job search is broken.** You're an AI/ML intern in Electronic City, Bengaluru. Bosch, Infosys, Wipro, TCS, and a dozen other tech campuses are within 5 km. But finding their internship postings means checking 15+ separate career pages every week. That's tedious, and you'll miss openings anyway.
- **General portals make it worse.** LinkedIn, Indeed, and Naukri show duplicates, stale listings, and irrelevant senior roles. Filtering for "AI/ML intern, Electronic City" returns noise.
- **No local aggregator exists.** Each company uses a different ATS (Greenhouse, Lever, Workday, etc.). There's no single place that watches them all for you.

## Solution

A lightweight, zero-cost agent that automates the entire pipeline:

1. **Discovers** tech companies near your location.
2. **Detects** the ATS platform (Greenhouse, Lever, Workday, etc.) each company uses.
3. **Crawls** career pages and extracts structured job data (title, location, description, apply link).
4. **Embeds** job descriptions using `sentence-transformers` (all-MiniLM-L6-v2) and computes cosine similarity against your resume/profile.
5. **Ranks & displays** results with match scores.

**Semantic search, not brittle keyword matching.** We embed both resumes and job descriptions into vectors so that *"Machine Learning Engineer"* semantically matches *"Deep Learning Engineer"* even if exact keywords differ. Cosine similarity on 384-dim embeddings captures meaning beyond keyword overlap.

For detailed rationale on architectural choices and trade-offs, see [DECISIONS.md](./DECISIONS.md).

## Features

- **Company Discovery Agent** — Geo-targeted list of nearby tech employers (Electronic City Phase I).
- **ATS Detector** — Pattern-matches URLs to identify Greenhouse, Lever, Workday, and other platforms.
- **Intelligent Crawler** — Uses public APIs where available (Greenhouse, Lever), falls back to static scraping.
- **Semantic Matching Engine** — CPU-only embeddings via `all-MiniLM-L6-v2`. No cloud API costs.
- **Resume-to-Job Scoring** — Cosine similarity between your resume text and each job description.
- **SQLite Persistence** — Zero-setup local database. No Docker, no cloud. Each design choice is deliberate: SQLite is serverless and trivial to migrate to Postgres later if needed.
- **FAISS Index** — Efficient vector search for fast nearest-neighbor queries as the dataset grows.

## Technology Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Rich ML/scraping ecosystem |
| Database | SQLite (built-in `sqlite3`) | Zero setup, single file. Deliberate MVP choice — Postgres comes later if needed. |
| Embeddings | `sentence-transformers` + `all-MiniLM-L6-v2` | 384-dim, fast on CPU, top of its size class on MTEB. Zero cost. |
| Vector Search | FAISS (CPU) | Open-source, handles millions of vectors locally. No cloud dependency. |
| Scraping | `requests` + `BeautifulSoup` | Lightweight, sufficient for 90% of target sites. Playwright added later for JS-heavy pages. |
| API Layer | FastAPI *(Phase 4+)* | Async, auto-docs. Not needed until the pipeline is wrapped in endpoints. |
| Frontend | React (Vite) + MUI *(Phase 5+)* | Modern component-based UI. Not built yet — the core logic comes first. |
| Alerting | Telegram Bot *(Phase 5+)* | Push notifications for high-match jobs. Added last. |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Company     │ ──▶ │  ATS         │ ──▶ │  Crawler     │
│  Discovery   │     │  Detector    │     │  & Extractor │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  (Future)    │ ◀── │  Ranked      │ ◀── │  Embedding   │
│  Dashboard   │     │  + Store     │     │  + Matching  │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Sample Output

| Company | Role | Match % | Experience | Location |
|---------|------|---------|------------|----------|
| Bosch Global Software Technologies | AI/ML Engineer Intern | 92% | 0-1 yr | Electronic City, Bengaluru |
| Infosys | Data Science Intern | 85% | 0-1 yr | Electronic City, Bengaluru |
| Wipro | Machine Learning Engineer | 78% | 1-2 yr | Electronic City, Bengaluru |
| TCS | Research Intern - ML/AI | 74% | 0-1 yr | Electronic City, Bengaluru |

## Setup

### Prerequisites

- Python 3.11+

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/Career_Intelligence_Agent.git
cd Career_Intelligence_Agent

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Configuration

**No API keys required.** The MVP uses:
- Public Greenhouse/Lever APIs (no auth).
- Local CPU-only embeddings (no cloud costs).
- SQLite database (auto-created).

### Running

```bash
# Phase 1: Fetch jobs from Greenhouse to JSON
python crawlers/greenhouse.py --board bosch

# Phase 2: Import into SQLite
python database/import.py

# Phase 3: Rank against your resume
python pipeline/rank.py --resume my_resume.txt
```

## Roadmap

```
Phase 0 — Research & Setup        [COMPLETE]
Phase 1 — MVP Crawlers             [IN PROGRESS]
Phase 2 — SQLite Storage           [UP NEXT]
Phase 3 — Semantic Layer           [PLANNED]
Phase 4 — FastAPI Backend          [PLANNED]
Phase 5 — React Frontend           [PLANNED]
```

See [ROADMAP.md](./ROADMAP.md) for detailed milestones and deliverables.

## Contributing

This project is in active early-stage development. Contributions, issues, and feature suggestions are welcome. The project is structured as independent modular agents, making it easy to extend or swap components.
