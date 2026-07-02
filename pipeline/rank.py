"""End-to-end ranking pipeline: SQLite → embeddings → FAISS → ranked output."""

import argparse
import json
import logging
import os
import sqlite3
import sys
from typing import Any

from database.crud import get_all_jobs
from embeddings.embedder import build_job_text, embed, embed_batch
from embeddings.matcher import compute_match_scores
from embeddings.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


def rank_jobs(
    db_path: str,
    resume_text: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Run the full ranking pipeline: load, embed, search, score, return.

    Args:
        db_path: Path to the SQLite database file.
        resume_text: Raw resume text to match against.
        top_k: Number of top results to return.

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

    # 3. Embed all job descriptions.
    logger.info("Embedding %d job descriptions...", len(job_texts))
    job_embeddings = embed_batch(job_texts)

    # 4. Build FAISS index.
    vector_store = FAISSVectorStore()
    vector_store.build(job_embeddings, job_ids)

    # 5. Embed the resume.
    logger.info("Embedding resume text...")
    resume_vector = embed(resume_text)

    # 6. Search FAISS for nearest neighbours.
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
    for job_id, match_score in zip(job_ids_found, match_scores):
        job = job_map.get(job_id)
        if job is None:
            continue
        enriched = dict(job)
        enriched["match_score"] = round(match_score, 1)
        ranked.append(enriched)

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
        lines.append(
            f"  {i:<3} {score:<8.1f} {company:<20} {title:<40} {location:<30}"
        )

    return "\n".join(lines)


def main() -> None:
    """CLI entry point for the ranking pipeline."""
    parser = argparse.ArgumentParser(
        description="Rank jobs in a SQLite database against a resume."
    )
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
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Read resume text.
    try:
        with open(args.resume, "r", encoding="utf-8") as f:
            resume_text = f.read().strip()
    except FileNotFoundError:
        print(f"Error: resume file not found: {args.resume}")
        sys.exit(1)

    if not resume_text:
        print("Error: resume file is empty")
        sys.exit(1)

    # Run ranking pipeline.
    ranked = rank_jobs(db_path=args.db, resume_text=resume_text, top_k=args.top_k)

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
