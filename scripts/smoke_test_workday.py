"""Smoke test all Workday companies in the registry.

Usage:
    python scripts/smoke_test_workday.py

Outputs:
    - workday_smoke_test_report.md  (detailed per-company report)
    - Console summary               (quick pass/fail overview)
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

# Minimal logging during smoke test.
logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
logger = logging.getLogger("smoke_test")

REPORT_PATH = Path("workday_smoke_test_report.md")

_PAGE_SIZE = 200
_SITE_PATTERNS = [
    "{tenant}ExternalCareerSite",
    "External",
    "{tenant}",
    "Careers",
    "External_Career_Site",
    "{tenant}_External_Career_Site",
    "{tenant}_Careers",
    "CareerSite",
]


# ── Data model ───────────────────────────────────────────────────────────────


@dataclass
class CompanyResult:
    company: str
    company_id: str
    tenant: str
    subdomain: str
    careers_url: str
    site_configured: str | None
    site_discovered: str | None
    navigation_ok: bool
    api_http_status: int | None
    api_response_preview: str
    job_count: int
    total_reported: int
    pages_fetched: int
    duration_seconds: float
    discovery_duration: float
    error: str | None

    @property
    def status(self) -> str:
        if self.api_http_status == 200 and self.job_count > 0:
            return "working"
        if self.api_http_status == 200 and self.job_count == 0 and self.total_reported == 0:
            return "no_jobs"
        if self.api_http_status == 200 and self.job_count == 0 and self.total_reported > 0:
            return "warnings"
        return "failed"

    @property
    def status_icon(self) -> str:
        return {"working": "[OK]", "no_jobs": "[--]", "warnings": "[!!]", "failed": "[XX]"}[self.status]


# ── Workday API helpers (standalone, no crawler dependency) ──────────────────


def build_host(tenant: str, subdomain: str) -> str:
    return f"{tenant}.{subdomain}.myworkdayjobs.com"


def build_api_url(tenant: str, subdomain: str, site: str) -> str:
    return f"https://{build_host(tenant, subdomain)}/wday/cxs/{tenant}/{site}/jobs"


def build_careers_url(tenant: str, subdomain: str, site: str | None = None) -> str:
    host = build_host(tenant, subdomain)
    if site:
        return f"https://{host}/{site}"
    return f"https://{host}/"


# ── Playwright test logic ────────────────────────────────────────────────────


_DIAGNOSTIC_SCRIPT_TEMPLATE = """
(async () => {
    const result = { success: false, jobs: [], total: 0, status: 0, pages: 0, error: null };
    try {
        const resp = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json", "x-calypso-csrf-token": CSRF_TOKEN },
            body: JSON.stringify({ limit: PAGE_SIZE, offset: 0, searchText: "" })
        });
        result.status = resp.status;
        if (!resp.ok) {
            let body = "";
            try { body = await resp.text(); } catch(e) {}
            result.error = `HTTP ${resp.status} ${resp.statusText}`;
            if (body) result.error += " | " + body.slice(0, 200);
            return result;
        }
        const data = await resp.json();
        result.success = true;
        result.total = data.total || 0;
        result.jobs = data.jobPostings || [];
        result.pages = 1;
    } catch (e) {
        result.error = String(e);
    }
    return result;
})()
"""


async def _is_maintenance_page(page: Any) -> bool:
    try:
        title = await page.title()
        if "currently unavailable" in title.lower():
            return True
        url = page.url
        return "maintenance" in url.lower()
    except Exception as e:
        logger.warning("_is_maintenance_page failed: %s", e)
        return False


async def _check_page_has_jobs(page: Any) -> bool:
    if await _is_maintenance_page(page):
        return False
    try:
        result = await page.evaluate("""
            () => {
                const hasAutomation = document.querySelectorAll('[data-automation-id]').length > 0;
                const title = document.title || '';
                const hasWorkdayTitle = title.includes('Workday') || title.includes('Careers') || title.includes('Jobs');
                const hasJobElements = document.querySelectorAll('[class*="job"], [id*="job"]').length > 3;
                return hasAutomation || hasWorkdayTitle || hasJobElements;
            }
        """)
        return bool(result)
    except Exception as e:
        logger.warning("_check_page_has_jobs failed: %s", e)
        return False


async def _extract_csrf_token(page: Any) -> str:
    try:
        raw = await page.evaluate("() => document.cookie")
        if not raw:
            return ""
        for part in raw.split("; "):
            if part.startswith("CALYPSO_CSRF_TOKEN="):
                return cast(str, part.split("=", 1)[1])
    except Exception as e:
        logger.warning("_extract_csrf_token failed: %s", e)
    return ""


async def test_one(page: Any, entry: dict) -> CompanyResult:
    company = entry["company"]
    company_id = entry["id"]
    tenant = entry.get("tenant", company_id)
    subdomain = entry.get("subdomain", "wd1")
    site_configured = entry.get("site")
    careers_url = entry.get("careers_url", build_careers_url(tenant, subdomain))

    t_start = time.time()
    discovered_site: str | None = site_configured
    navigation_ok = False
    api_http_status: int | None = None
    api_preview = ""
    job_count = 0
    total_reported = 0
    pages = 0
    error: str | None = None
    discovery_duration = 0.0

    try:
        if not discovered_site:
            # Discovery: redirect tracking + page content validation.
            base_url = build_careers_url(tenant, subdomain)
            logger.info("  Discovering site at %s", base_url)
            t_disc = time.time()

            nav_ok = False
            try:
                await page.goto(base_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                final_url = page.url
                path = final_url.rstrip("/").split(".myworkdayjobs.com")[-1]
                if path and path != "/":
                    candidate = path.lstrip("/")
                    if candidate and await _check_page_has_jobs(page):
                        discovered_site = candidate
                        nav_ok = True
            except Exception as e:
                logger.warning("Site discovery navigation failed for %s/%s: %s", subdomain, tenant, e)

            if not discovered_site:
                for pattern in _SITE_PATTERNS:
                    candidate = pattern.format(tenant=tenant)
                    url = build_careers_url(tenant, subdomain, candidate)
                    try:
                        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        if await _check_page_has_jobs(page):
                            discovered_site = candidate
                            nav_ok = True
                            break
                    except Exception as e:
                        logger.warning("Pattern navigation failed for %s/%s (%s): %s", subdomain, tenant, candidate, e)
                        continue

            discovery_duration = time.time() - t_disc
            navigation_ok = nav_ok or discovered_site is not None

        if not discovered_site and not error and await _is_maintenance_page(page):
            error = "Workday site is in maintenance mode (global outage)"

        if discovered_site:
            # Navigate to the correct careers page (if not already there).
            page_url = build_careers_url(tenant, subdomain, discovered_site)
            try:
                await page.goto(page_url, timeout=30000, wait_until="networkidle")
                await asyncio.sleep(2)
                navigation_ok = True
            except Exception as e:
                if not navigation_ok:
                    error = f"Navigation failed: {e}"
                    navigation_ok = False

        if navigation_ok and discovered_site:
            # Extract CSRF token and call API via page.evaluate.
            csrf_token = await _extract_csrf_token(page)
            api_url = build_api_url(tenant, subdomain, discovered_site)
            script = (
                _DIAGNOSTIC_SCRIPT_TEMPLATE.replace("API_URL", json.dumps(api_url))
                .replace("PAGE_SIZE", str(_PAGE_SIZE))
                .replace("CSRF_TOKEN", json.dumps(csrf_token))
            )
            try:
                result = await page.evaluate(script)
                api_http_status = result.get("status")
                if result.get("success"):
                    total_reported = result.get("total", 0)
                    job_count = len(result.get("jobs", []))
                    pages = result.get("pages", 0)
                else:
                    error = result.get("error") or "API call failed"
                    api_preview = (result.get("error") or "")[:200]
            except Exception as e:
                error = f"evaluate exception: {e}"
        elif not discovered_site:
            error = "Site discovery failed — all patterns returned no match"

    except Exception as e:
        if not error:
            error = f"Unexpected error: {e}"

    duration = time.time() - t_start

    return CompanyResult(
        company=company,
        company_id=company_id,
        tenant=tenant,
        subdomain=subdomain,
        careers_url=careers_url,
        site_configured=site_configured,
        site_discovered=discovered_site,
        navigation_ok=navigation_ok,
        api_http_status=api_http_status,
        api_response_preview=api_preview,
        job_count=job_count,
        total_reported=total_reported,
        pages_fetched=pages,
        duration_seconds=duration,
        discovery_duration=discovery_duration,
        error=error,
    )


# ── Report generation ────────────────────────────────────────────────────────


def _root_cause(result: CompanyResult) -> str:
    if result.error:
        if "maintenance" in result.error.lower():
            return "Workday site is in maintenance mode (global outage)"
        if "Navigation failed" in result.error or "Timeout" in result.error:
            return "Page navigation failed / timeout"
        if "Site discovery failed" in result.error:
            return "Site name not found — no pattern matched"
        if "HTTP 403" in result.error or "HTTP 401" in result.error:
            return "API returned 401/403 — likely Cloudflare WAF blocking even browser fetch"
        if "HTTP 404" in result.error:
            return "API returned 404 — site name or tenant may be wrong"
        if "HTTP 422" in result.error:
            return "API returned 422 — Unprocessable Entity (malformed request)"
        if "HTTP" in (result.error or ""):
            return f"API HTTP {result.api_http_status}"
        return result.error[:100]
    return ""


def generate_report(results: list[CompanyResult]) -> str:
    working = sum(1 for r in results if r.status == "working")
    no_jobs = sum(1 for r in results if r.status == "no_jobs")
    warnings = sum(1 for r in results if r.status == "warnings")
    failed = sum(1 for r in results if r.status == "failed")
    total_jobs = sum(r.job_count for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    lines = []
    lines.append("# Workday Smoke Test Report")
    lines.append("")
    lines.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total companies tested | {len(results)} |")
    lines.append(f"| [OK] Working | {working} |")
    lines.append(f"| [--] No active jobs | {no_jobs} |")
    lines.append(f"| [!!] Working with warnings | {warnings} |")
    lines.append(f"| [XX] Failed | {failed} |")
    lines.append(f"| Total jobs fetched | {total_jobs} |")
    lines.append(f"| Total execution time | {total_duration:.1f}s |")
    lines.append("")

    lines.append("## Per-Company Results")
    lines.append("")
    for r in results:
        status_map = {"working": "OK", "no_jobs": "--", "warnings": "!!", "failed": "XX"}
        lines.append(f"### [{status_map[r.status]}] {r.company} (`{r.company_id}`)")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Careers URL | `{r.careers_url}` |")
        lines.append(f"| Tenant / Subdomain | `{r.tenant}` / `{r.subdomain}` |")
        lines.append(f"| Site (configured) | `{r.site_configured or '—'}` |")
        lines.append(f"| Site (discovered) | `{r.site_discovered or '—'}` |")
        lines.append(f"| Navigation OK | {r.navigation_ok} |")
        lines.append(f"| API HTTP status | {r.api_http_status or '—'} |")
        lines.append(f"| Jobs fetched | {r.job_count} |")
        lines.append(f"| Total reported | {r.total_reported} |")
        lines.append(f"| Pages fetched | {r.pages_fetched} |")
        lines.append(f"| Duration | {r.duration_seconds:.1f}s (discovery: {r.discovery_duration:.1f}s) |")
        if r.error:
            lines.append(f"| Error | {r.error} |")
        if r.status != "working":
            lines.append(f"| Root cause | {_root_cause(r)} |")
        lines.append("")

    lines.append("## Root Cause Summary")
    lines.append("")
    causes: dict[str, int] = {}
    for r in results:
        if r.status != "working":
            cause = _root_cause(r)
            causes[cause] = causes.get(cause, 0) + 1
    if causes:
        lines.append("| Root cause | Count |")
        lines.append("|------------|-------|")
        for cause, count in sorted(causes.items(), key=lambda x: -x[1]):
            lines.append(f"| {cause} | {count} |")
    else:
        lines.append("All companies working — no failures.")
    lines.append("")

    return "\n".join(lines)


def print_console_summary(results: list[CompanyResult]) -> None:
    working = [r for r in results if r.status == "working"]
    no_jobs = [r for r in results if r.status == "no_jobs"]
    warnings = [r for r in results if r.status == "warnings"]
    failed = [r for r in results if r.status == "failed"]
    total_jobs = sum(r.job_count for r in results)
    total_duration = sum(r.duration_seconds for r in results)

    print()
    print("=" * 65)
    print("  Workday Smoke Test — Summary")
    print("=" * 65)
    print(f"  Tested:    {len(results)} companies")
    print(f"  [OK] Working: {len(working)}")
    print(f"  [--] No jobs: {len(no_jobs)}")
    print(f"  [!!] Warnings: {len(warnings)}")
    print(f"  [XX] Failed:  {len(failed)}")
    print(f"  Jobs:    {total_jobs}")
    print(f"  Duration: {total_duration:.0f}s")
    print()
    if working:
        print("  [OK] Working:")
        for r in working:
            print(f"    {r.company:25s} {r.job_count:4d} jobs  {r.duration_seconds:5.1f}s")
    if no_jobs:
        print("  [--] No active jobs:")
        for r in no_jobs:
            print(f"    {r.company:25s} site={r.site_discovered or '?'}")
    if warnings:
        print("  [!!] Warnings:")
        for r in warnings:
            print(f"    {r.company:25s} {r.error or ''}")
    if failed:
        print("  [XX] Failed:")
        for r in failed:
            cause = _root_cause(r)[:60]
            print(f"    {r.company:25s} {cause}")
    print("=" * 65)


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    registry_path = Path("data/companies.yml")
    if not registry_path.exists():
        print("ERROR: data/companies.yml not found")
        return 1

    with open(registry_path) as f:
        registry = yaml.safe_load(f)

    companies = [c for c in registry.get("companies", []) if c.get("platform") == "workday" and c.get("enabled", True)]

    print(f"Loaded {len(companies)} Workday companies from registry")
    print("Starting smoke test (one browser session per company)...")
    print()

    results: list[CompanyResult] = []

    async def _run_all():
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()

            for i, entry in enumerate(companies, 1):
                company = entry["company"]
                print(f"  [{i}/{len(companies)}] {company} ...", end=" ", flush=True)
                page = await context.new_page()
                try:
                    result = await test_one(page, entry)
                    results.append(result)
                    icon = result.status_icon
                    jobs = result.job_count
                    dur = result.duration_seconds
                    print(f"{icon}  {jobs} jobs  {dur:.1f}s")
                except Exception as e:
                    print(f"[XX] exception: {e}")
                    tenant = entry.get("tenant", entry["id"])
                    results.append(
                        CompanyResult(
                            company=company,
                            company_id=entry["id"],
                            tenant=tenant,
                            subdomain=entry.get("subdomain", "wd1"),
                            careers_url=entry.get("careers_url", ""),
                            site_configured=entry.get("site"),
                            site_discovered=None,
                            navigation_ok=False,
                            api_http_status=None,
                            api_response_preview="",
                            job_count=0,
                            total_reported=0,
                            pages_fetched=0,
                            duration_seconds=0,
                            discovery_duration=0,
                            error=str(e),
                        )
                    )
                finally:
                    await page.close()

            await browser.close()

    asyncio.run(_run_all())

    # Generate report.
    report = generate_report(results)
    REPORT_PATH.write_text(report, encoding="utf-8")

    # Console summary.
    print_console_summary(results)

    print(f"\nDetailed report written to {REPORT_PATH}")
    return 0 if sum(1 for r in results if r.status == "failed") == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
