"""End-to-end verification script — tests each crawler platform against a real API."""

import json
import logging
import sys
import time
from typing import Any

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

PASS = 0
FAIL = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        logger.info("  PASS | %s | %s", label, detail)
    else:
        FAIL += 1
        logger.error("  FAIL | %s | %s", label, detail)


def verify_greenhouse():
    logger.info("[Greenhouse] Testing phonepe...")
    t0 = time.time()
    r = requests.get("https://boards-api.greenhouse.io/v1/boards/phonepe/jobs", timeout=30)
    elapsed = time.time() - t0
    check("status", r.status_code == 200, f"{r.status_code} ({elapsed:.1f}s)")
    if r.status_code == 200:
        data = r.json()
        jobs = data.get("jobs", [])
        check("has jobs array", isinstance(jobs, list), f"{len(jobs)} jobs")
        if jobs:
            check("first job has title", bool(jobs[0].get("title")), f"title='{jobs[0].get('title', '')}'")
            check("first job has id", bool(jobs[0].get("id")), f"id={jobs[0].get('id', '')}")


def verify_lever():
    logger.info("[Lever] Testing cred...")
    t0 = time.time()
    r = requests.get("https://api.lever.co/v0/postings/cred?mode=json", timeout=30)
    elapsed = time.time() - t0
    check("status", r.status_code == 200, f"{r.status_code} ({elapsed:.1f}s)")
    if r.status_code == 200:
        jobs = r.json()
        check("response is list", isinstance(jobs, list), f"{len(jobs)} jobs")
        if jobs:
            check("first job has text", bool(jobs[0].get("text")), f"text='{jobs[0].get('text', '')}'")


def verify_workday(subdomain: str, tenant: str, label: str):
    logger.info("[Workday] Testing %s (%s/%s)...", label, subdomain, tenant)
    url = f"https://{subdomain}.myworkdayjobs.com/wday/cxs/{subdomain}/{tenant}/jobs"
    payload = {"limit": 5, "offset": 0, "searchText": ""}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    t0 = time.time()
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
    except Exception as e:
        elapsed = time.time() - t0
        check(f"status ({label})", False, f"Exception: {e} ({elapsed:.1f}s)")
        return
    elapsed = time.time() - t0
    check(f"status ({label})", r.status_code == 200, f"{r.status_code} ({elapsed:.1f}s)")
    if r.status_code == 200:
        data = r.json()
        jobs = data.get("jobPostings", [])
        check(f"has jobPostings ({label})", isinstance(jobs, list), f"{len(jobs)} jobs")
        if jobs:
            check(f"first job has title ({label})", bool(jobs[0].get("title")), f"title='{jobs[0].get('title', '')}'")
            check(f"first job has externalPath ({label})", bool(jobs[0].get("externalPath")), f"path='{jobs[0].get('externalPath', '')}'")
    else:
        logger.info("  Response body: %s", r.text[:300])


def verify_ashby():
    logger.info("[Ashby] Testing sarvam...")
    t0 = time.time()
    r = requests.get("https://api.ashbyhq.com/posting-api/job-board/sarvam", timeout=30)
    elapsed = time.time() - t0
    check("status", r.status_code == 200, f"{r.status_code} ({elapsed:.1f}s)")
    if r.status_code == 200:
        data = r.json()
        jobs = data.get("jobs", [])
        check("has jobs array", isinstance(jobs, list), f"{len(jobs)} jobs")
        if jobs:
            check("first job has title", bool(jobs[0].get("title")), f"title='{jobs[0].get('title', '')}'")
            check("first job has id", bool(jobs[0].get("id")), f"id={jobs[0].get('id', '')}")


def verify_smartrecruiters():
    logger.info("[SmartRecruiters] Testing FractalAnalytics...")
    t0 = time.time()
    r = requests.get("https://api.smartrecruiters.com/v1/companies/FractalAnalytics/postings?limit=5", timeout=30)
    elapsed = time.time() - t0
    check("status", r.status_code == 200, f"{r.status_code} ({elapsed:.1f}s)")
    if r.status_code == 200:
        data = r.json()
        content = data.get("content", [])
        check("has content array", isinstance(content, list), f"{len(content)} jobs")
        if content:
            check("first job has name", bool(content[0].get("name")), f"name='{content[0].get('name', '')}'")
            check("first job has uuid", bool(content[0].get("uuid")), f"uuid={content[0].get('uuid', '')}")
        total = data.get("totalFound", 0)
        check("totalFound present", isinstance(total, int), f"totalFound={total}")
    else:
        logger.info("  Response body: %s", r.text[:300])


def verify_workable():
    logger.info("[Workable] Testing tiger-analytics...")
    t0 = time.time()
    r = requests.get("https://apply.workable.com/api/v1/widget/accounts/tiger-analytics?details=true", timeout=30)
    elapsed = time.time() - t0
    check("status", r.status_code == 200, f"{r.status_code} ({elapsed:.1f}s)")
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, dict):
            jobs = data.get("jobs", [])
        elif isinstance(data, list):
            jobs = data
        else:
            jobs = []
        check("has jobs", isinstance(jobs, list), f"{len(jobs)} jobs")
        if jobs:
            first = jobs[0] if isinstance(jobs[0], dict) else {}
            check("first job has title", bool(first.get("title")), f"title='{first.get('title', '')}'")
    else:
        logger.info("  Response body: %s", r.text[:300])


def verify_swiggy():
    """Verify Swiggy MyNextHire API."""
    from crawlers.custom.swiggy_careers import SwiggyCrawler
    logger.info("[Swiggy] Testing MyNextHire API...")
    t0 = time.time()
    c = SwiggyCrawler("swiggy", "Swiggy")
    jobs = c.fetch_jobs()
    elapsed = time.time() - t0
    check("fetched jobs", len(jobs) > 0, f"{len(jobs)} jobs ({elapsed:.1f}s)")
    if jobs:
        check("has title", bool(jobs[0].get("title")), f"title='{jobs[0].get('title', '')}'")
        check("has source", jobs[0].get("source") == "swiggy_careers", f"source={jobs[0].get('source')}")


def verify_tredence():
    """Verify Tredence RippleHire API."""
    from crawlers.custom.tredence_careers import TredenceCrawler
    logger.info("[Tredence] Testing RippleHire API...")
    t0 = time.time()
    c = TredenceCrawler("tredence", "Tredence")
    jobs = c.fetch_jobs()
    elapsed = time.time() - t0
    check("fetched jobs", len(jobs) > 0, f"{len(jobs)} jobs ({elapsed:.1f}s)")
    if jobs:
        check("has title", bool(jobs[0].get("title")), f"title='{jobs[0].get('title', '')}'")
        check("has source", jobs[0].get("source") == "tredence_careers", f"source={jobs[0].get('source')}")


def main():
    global PASS, FAIL
    print("=" * 60)
    print("  Crawler End-to-End Verification")
    print("=" * 60)
    print()

    # Verifying all platforms
    verify_greenhouse()
    verify_lever()
    verify_workday("wd5", "Adobe", "Adobe (wd5)")
    verify_workday("wd1", "Microsoft", "Microsoft (wd1)")
    verify_workday("wd1", "ServiceNow", "ServiceNow (blocked?)")
    verify_ashby()
    verify_smartrecruiters()
    verify_workable()
    verify_swiggy()
    verify_tredence()

    print()
    print("=" * 60)
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
