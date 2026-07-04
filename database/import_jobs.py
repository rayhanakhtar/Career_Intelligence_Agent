"""CLI script to import job records from JSON files into SQLite."""

import argparse
import json
import logging
import sqlite3

from database.crud import insert_job
from database.schema import create_tables

logger = logging.getLogger(__name__)


def import_json_to_db(db_path: str, json_paths: list[str]) -> int:
    """Import job records from one or more JSON files into SQLite.

    Each JSON file should contain a list of job record dictionaries matching
    the schema produced by crawlers/greenhouse.py and crawlers/lever.py.

    Args:
        db_path: Path to the SQLite database file (will be created if missing).
        json_paths: List of paths to JSON files containing job records.

    Returns:
        Total number of job records imported.
    """
    conn = sqlite3.connect(db_path)
    create_tables(conn)

    total = 0
    for path in json_paths:
        try:
            with open(path, encoding="utf-8") as f:
                records = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Skipping %s: %s", path, e)
            continue

        if not isinstance(records, list):
            logger.warning("Skipping %s: expected a list of records", path)
            continue

        for record in records:
            insert_job(conn, record)
            total += 1

        logger.info("Imported %d records from %s", len(records), path)

    conn.close()
    return total


def main() -> None:
    """Entry point for the CLI import script."""
    parser = argparse.ArgumentParser(description="Import job JSON files into a SQLite database.")
    parser.add_argument(
        "--db",
        default="jobs.db",
        help="Path to the SQLite database file (default: jobs.db)",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="One or more JSON files containing job records to import",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    total = import_json_to_db(args.db, args.files)
    print(f"Imported {total} job(s) into {args.db}")


if __name__ == "__main__":
    main()
