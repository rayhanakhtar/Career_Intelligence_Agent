"""End-to-end ranking pipeline: SQLite → embeddings → FAISS → ranked output."""

import argparse
import json
import logging
import os
import sqlite3
import sys
from typing import Any

from database.crud import count_jobs, get_all_jobs
from embeddings.embedder import build_job_text, embed, embed_batch
from embeddings.matcher import compute_match_scores
from embeddings.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)

LOCATION_BOOST: float = 1.5

_FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "faiss_index")

# Module-level cache to avoid rebuilding the index on every search.
_cached_db_path: str | None = None
_cached_job_count: int = -1
_cached_vector_store: FAISSVectorStore | None = None


def _get_cached_index(db_path: str) -> FAISSVectorStore | None:
    """Return a cached FAISS index, rebuilding only if the DB has changed.

    The index is persisted to ``_FAISS_INDEX_DIR`` and loaded on the first
    call. Subsequent calls reuse the cached in-memory index unless the
    job count in the database has changed (indicating a new crawl).
    """
    global _cached_db_path, _cached_job_count, _cached_vector_store

    # Count jobs in the database.
    conn = sqlite3.connect(db_path)
    try:
        current_count = count_jobs(conn)
    finally:
        conn.close()

    # If the DB path and job count match the cached index, reuse it.
    if _cached_db_path == db_path and _cached_job_count == current_count and _cached_vector_store is not None:
        logger.debug("Reusing cached FAISS index (%d jobs)", current_count)
        return _cached_vector_store

    # Otherwise, try to load from disk first.
    if os.path.isdir(_FAISS_INDEX_DIR):
        try:
            store = FAISSVectorStore()
            store.load(_FAISS_INDEX_DIR)
            logger.info("Loaded FAISS index from disk (%d vectors)", len(store.id_map))
            _cached_db_path = db_path
            _cached_job_count = current_count
            _cached_vector_store = store
            return store
        except (FileNotFoundError, RuntimeError) as e:
            logger.info("Could not load cached FAISS index: %s", e)

    # No cache available — caller will build and save.
    _cached_db_path = None
    _cached_job_count = -1
    _cached_vector_store = None
    return None


def _cache_and_persist(store: FAISSVectorStore, db_path: str, job_count: int) -> None:
    """Update the module-level cache and persist to disk."""
    global _cached_db_path, _cached_job_count, _cached_vector_store

    _cached_db_path = db_path
    _cached_job_count = job_count
    _cached_vector_store = store

    try:
        store.save(_FAISS_INDEX_DIR)
        logger.info("Persisted FAISS index to %s (%d vectors)", _FAISS_INDEX_DIR, job_count)
    except Exception as e:
        logger.warning("Failed to persist FAISS index: %s", e)


def invalidate_index_cache() -> None:
    """Force the FAISS index to be rebuilt on the next search.

    Called by :class:`CrawlService` after a crawl completes so that new
    jobs are included in subsequent searches.
    """
    global _cached_db_path, _cached_job_count, _cached_vector_store
    _cached_db_path = None
    _cached_job_count = -1
    _cached_vector_store = None
    logger.debug("FAISS index cache invalidated")


def _apply_location_boost(
    ranked: list[dict[str, Any]],
    preferred_locations: list[str],
) -> None:
    """Apply a score multiplier to jobs whose location matches preferred locations.

    Mutates the ``match_score`` of matching entries in place.

    Args:
        ranked: List of job records with a ``match_score`` key.
        preferred_locations: Location strings to match against job locations.
    """
    for job in ranked:
        job_location = job.get("location", "").lower()
        for pref in preferred_locations:
            if pref.lower() in job_location:
                job["match_score"] = round(job["match_score"] * LOCATION_BOOST, 1)
                break


def rank_jobs(
    db_path: str,
    resume_text: str,
    top_k: int = 10,
    preferred_locations: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Run the full ranking pipeline: load, embed, search, score, return.

    Args:
        db_path: Path to the SQLite database file.
        resume_text: Raw resume text to match against.
        top_k: Number of top results to return.
        preferred_locations: Optional list of location strings to boost
            (e.g. ``["Bengaluru", "Electronic City"]``). Matching jobs get a
            score multiplier of ``LOCATION_BOOST`` (1.5x).

    Returns:
        A list of job record dictionaries enriched with a ``match_score`` key,
        sorted by descending match score.
    """
    # 1. Load all jobs from SQLite.
    conn = sqlite3.connect(db_path)
    all_jobs = get_all_jobs(conn)
    conn.close()

    if not all_jobs:
        logger.warning("No jobs found in database %s", db_path)
        return []

    logger.info("Loaded %d jobs from %s", len(all_jobs), db_path)

    # 2. Build searchable text for each job.
    job_texts = [build_job_text(job) for job in all_jobs]
    job_ids = [job["id"] for job in all_jobs]

    # 3. Try to use cached FAISS index.
    vector_store = _get_cached_index(db_path)

    if vector_store is None:
        # 4. Embed all job descriptions (cache miss).
        logger.info("Embedding %d job descriptions...", len(job_texts))
        job_embeddings = embed_batch(job_texts)

        # 5. Build FAISS index.
        vector_store = FAISSVectorStore()
        vector_store.build(job_embeddings, job_ids)

        # 6. Persist to disk for next search.
        _cache_and_persist(vector_store, db_path, len(all_jobs))
    else:
        logger.info("Using cached FAISS index with %d jobs", len(all_jobs))

    # 7. Embed the resume.
    logger.info("Embedding resume text...")
    resume_vector = embed(resume_text)

    # 8. Search FAISS for nearest neighbours.
    logger.info("Searching for top %d matches...", top_k)
    raw_results = vector_store.search(resume_vector, k=top_k)

    if not raw_results:
        return []

    # 7. Compute match scores.
    job_ids_found = [r[0] for r in raw_results]
    raw_scores = [r[1] for r in raw_results]
    match_scores = compute_match_scores(raw_scores)

    # 8. Join with job metadata and sort by match score descending.
    job_map = {job["id"]: job for job in all_jobs}
    ranked: list[dict[str, Any]] = []
    for job_id, match_score in zip(job_ids_found, match_scores, strict=True):
        job = job_map.get(job_id)
        if job is None:
            continue
        enriched = dict(job)
        enriched["match_score"] = round(match_score, 1)
        ranked.append(enriched)

    if preferred_locations:
        _apply_location_boost(ranked, preferred_locations)

    ranked.sort(key=lambda j: j["match_score"], reverse=True)
    return ranked


def format_table(ranked: list[dict[str, Any]]) -> str:
    """Format ranked jobs as a human-readable ASCII table.

    Args:
        ranked: List of enriched job records.

    Returns:
        A formatted string table.
    """
    lines = []
    lines.append(f"  {'#':<3} {'Match%':<8} {'Company':<20} {'Title':<40} {'Location':<30}")
    lines.append("  " + "-" * 105)

    for i, job in enumerate(ranked, start=1):
        score = job.get("match_score", 0)
        company = job.get("company", "")[:18]
        title = job.get("title", "")[:38]
        location = job.get("location", "")[:28]
        lines.append(f"  {i:<3} {score:<8.1f} {company:<20} {title:<40} {location:<30}")

    return "\n".join(lines)


def main() -> None:
    """CLI entry point for the ranking pipeline."""
    parser = argparse.ArgumentParser(description="Rank jobs in a SQLite database against a resume.")
    parser.add_argument(
        "--db",
        default="jobs.db",
        help="Path to the SQLite database file (default: jobs.db)",
    )
    parser.add_argument(
        "--resume",
        required=True,
        help="Path to a text file containing the resume to match against",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top matches to return (default: 10)",
    )
    parser.add_argument(
        "--locations",
        type=str,
        default="",
        help="Comma-separated preferred locations for boosting (e.g. Bengaluru,Electronic City)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Read resume text.
    try:
        with open(args.resume, encoding="utf-8") as f:
            resume_text = f.read().strip()
    except FileNotFoundError:
        print(f"Error: resume file not found: {args.resume}")
        sys.exit(1)

    if not resume_text:
        print("Error: resume file is empty")
        sys.exit(1)

    locations = [loc.strip() for loc in args.locations.split(",") if loc.strip()] or None

    ranked = rank_jobs(
        db_path=args.db,
        resume_text=resume_text,
        top_k=args.top_k,
        preferred_locations=locations,
    )

    if not ranked:
        print("No matches found.")
        return

    # Print table.
    print("\nRanked Jobs\n")
    print(format_table(ranked))
    print()

    # Save JSON.
    output_path = "ranked_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2, ensure_ascii=False)
    print(f"Saved ranked results to {output_path}")


if __name__ == "__main__":
    main()
