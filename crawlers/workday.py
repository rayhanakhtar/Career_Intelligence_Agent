"""Crawler for Workday ATS via hybrid Playwright+requests approach.

Strategy (in order):
1. Try ``requests`` directly (fast path — some tenants bypass WAF).
2. On failure, use a single Playwright session to discover the career
   site and fetch all jobs via browser ``fetch`` (``page.evaluate``).
"""

import asyncio
import json
import logging
import time
from typing import Any, cast

import requests

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

_PAGE_SIZE = 200
_MAX_PAGE_RETRIES = 3

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


def _build_workday_host(tenant: str, subdomain: str) -> str:
    return f"{tenant}.{subdomain}.myworkdayjobs.com"


def _build_api_url(tenant: str, subdomain: str, site: str) -> str:
    host = _build_workday_host(tenant, subdomain)
    return f"https://{host}/wday/cxs/{tenant}/{site}/jobs"


def _build_careers_url(tenant: str, subdomain: str, site: str | None = None) -> str:
    host = _build_workday_host(tenant, subdomain)
    if site:
        return f"https://{host}/{site}"
    return f"https://{host}/"


def _fetch_page_requests(
    tenant: str,
    subdomain: str,
    site: str,
    offset: int = 0,
    limit: int = _PAGE_SIZE,
    session: requests.Session | None = None,
) -> dict[str, Any] | None:
    url = _build_api_url(tenant, subdomain, site)
    payload = {"limit": limit, "offset": offset, "searchText": ""}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.55 Safari/537.36",
    }

    sess = session or requests.Session()

    last_error: Exception | None = None
    for attempt in range(1, _MAX_PAGE_RETRIES + 1):
        try:
            if attempt > 1:
                backoff = 2 ** (attempt - 1)
                logger.info(
                    "Retry %d/%d for Workday %s/%s (site=%s) offset=%d backoff=%ds",
                    attempt - 1,
                    _MAX_PAGE_RETRIES,
                    subdomain,
                    tenant,
                    site,
                    offset,
                    backoff,
                )
                time.sleep(backoff)

            response = sess.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return cast(dict[str, Any] | None, response.json())

        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(
                "Timeout on Workday %s/%s (site=%s) offset=%d (attempt %d/%d)",
                subdomain,
                tenant,
                site,
                offset,
                attempt,
                _MAX_PAGE_RETRIES,
            )
        except requests.exceptions.HTTPError as e:
            last_error = e
            status = e.response.status_code if e.response is not None else 0
            logger.warning(
                "HTTP %d on Workday %s/%s (site=%s) offset=%d (attempt %d/%d)",
                status,
                subdomain,
                tenant,
                site,
                offset,
                attempt,
                _MAX_PAGE_RETRIES,
            )
            if status in (401, 403, 406, 422):
                return None
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning("Request failed for Workday %s/%s offset=%d: %s", subdomain, tenant, offset, e)

    logger.error("All retries exhausted for Workday %s/%s offset=%d: %s", subdomain, tenant, offset, last_error)
    return None


def _discover_site(
    tenant: str,
    subdomain: str,
) -> str | None:
    for pattern in _SITE_PATTERNS:
        site = pattern.format(tenant=tenant)
        url = _build_api_url(tenant, subdomain, site)
        try:
            r = requests.post(
                url,
                json={"limit": 1, "offset": 0, "searchText": ""},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
                timeout=15,
            )
            if r.status_code == 200:
                logger.info("Discovered Workday site '%s' for %s/%s via pattern", site, subdomain, tenant)
                return site
        except requests.RequestException:
            continue

    logger.info("Site discovery via patterns failed for %s/%s", subdomain, tenant)
    return None


def _build_job_record(
    job: dict[str, Any], display_name: str, tenant: str, subdomain: str, _site: str
) -> dict[str, Any]:
    ext_path = job.get("externalPath") or ""
    if ext_path.startswith("/"):
        host = _build_workday_host(tenant, subdomain)
        apply_url = f"https://{host}{ext_path}"
    else:
        apply_url = ""

    bullet_fields = job.get("bulletFields") or []
    source_id = str(bullet_fields[0]) if bullet_fields else str(job.get("jobPostingId") or job.get("id") or "")

    return {
        "title": job.get("title") or "",
        "company": display_name,
        "location": job.get("locationsText") or "",
        "description": "",
        "apply_url": apply_url,
        "department": "",
        "employment_type": "",
        "posted_at": job.get("postedOn") or "",
        "source": "workday",
        "source_id": source_id,
    }


# ── Playwright internal helpers ──────────────────────────────────────────────


async def _is_maintenance_page(page: Any) -> bool:
    """Check if the page is the Workday maintenance/unavailable page."""
    try:
        title = await page.title()
        if "currently unavailable" in title.lower():
            return True
        url = page.url
        return "maintenance" in url.lower()
    except Exception:
        return False


async def _check_page_has_jobs(page: Any) -> bool:
    """Rough sanity check — does the page look like a Workday careers page?"""
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
    except Exception:
        return False


async def _discover_site_on_page(page: Any, tenant: str, subdomain: str) -> str | None:
    """Discover the career site name for a Workday tenant.

    Strategy:
    1. Navigate to the base domain.  Workday often redirects to a site path
       (e.g. ``/Microsoft``).  The redirect target is the site name.
    2. If no redirect, try each URL pattern from ``_SITE_PATTERNS`` and
       check whether the page loads successfully with Workday content.
    """
    base_url = f"https://{tenant}.{subdomain}.myworkdayjobs.com/"

    # Step 1 — navigate to base URL and capture any redirect path.
    try:
        await page.goto(base_url, timeout=20000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        final_url = page.url
        # If the final URL has a path component beyond "/", use it as site.
        path = final_url.rstrip("/").split(".myworkdayjobs.com")[-1]
        if path and path != "/":
            candidate = path.lstrip("/")
            if candidate and await _check_page_has_jobs(page):
                logger.info("Discovered Workday site '%s' for %s/%s via redirect", candidate, subdomain, tenant)
                return cast(str | None, candidate)
    except Exception as e:
        logger.warning("Site discovery navigation failed for %s/%s: %s", subdomain, tenant, e)

    # Step 2 — try each pattern URL.
    for pattern in _SITE_PATTERNS:
        candidate = pattern.format(tenant=tenant)
        url = f"https://{tenant}.{subdomain}.myworkdayjobs.com/{candidate}"
        try:
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            # If navigation didn't throw and page looks like Workday.
            if await _check_page_has_jobs(page):
                logger.info(
                    "Discovered Workday site '%s' for %s/%s via pattern '%s'", candidate, subdomain, tenant, pattern
                )
                return candidate
        except Exception:
            continue

    return None


async def _extract_csrf_token(page: Any) -> str:
    """Extract ``CALYPSO_CSRF_TOKEN`` from ``document.cookie``."""
    try:
        raw = await page.evaluate("() => document.cookie")
        if not raw:
            return ""
        for part in raw.split("; "):
            if part.startswith("CALYPSO_CSRF_TOKEN="):
                return cast(str, part.split("=", 1)[1])
    except Exception as e:
        logger.warning("Failed to extract CSRF token: %s", e)
    return ""


async def _fetch_jobs_on_page(page: Any, tenant: str, subdomain: str, site: str) -> list[dict[str, Any]] | None:
    """Fetch all jobs via ``page.evaluate`` using browser ``fetch``.

    Automatically extracts and includes the ``x-calypso-csrf-token``
    header required by the Workday CXS API.
    """
    api_url = _build_api_url(tenant, subdomain, site)
    csrf_token = await _extract_csrf_token(page)
    page_size = _PAGE_SIZE

    script = f"""
        (async () => {{
            const allJobs = [];
            let offset = 0;
            let total = Infinity;
            const pageSize = {json.dumps(page_size)};
            const apiUrl = {json.dumps(api_url)};
            const headers = {
        json.dumps(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-calypso-csrf-token": csrf_token,
            }
        )
    };

            while (offset < total) {{
                try {{
                    const resp = await fetch(apiUrl, {{
                        method: "POST",
                        headers: headers,
                        body: JSON.stringify({{
                            limit: pageSize,
                            offset: offset,
                            searchText: ""
                        }})
                    }});
                    if (!resp.ok) break;
                    const data = await resp.json();
                    const jobs = data.jobPostings || [];
                    allJobs.push(...jobs);
                    total = data.total || 0;
                    offset += pageSize;
                }} catch (e) {{
                    break;
                }}
            }}
            return allJobs;
        }})()
    """

    try:
        all_jobs = await page.evaluate(script)
        if isinstance(all_jobs, list) and len(all_jobs) > 0:
            return all_jobs
        logger.debug("page.evaluate returned no jobs for %s/%s (site=%s)", subdomain, tenant, site)
        return None
    except Exception as e:
        logger.warning("page.evaluate failed for %s/%s: %s", subdomain, tenant, e)
        return None


def _fetch_workday_playwright(
    tenant: str,
    subdomain: str,
    site: str | None = None,
) -> list[dict[str, Any]] | None:
    """Single Playwright session: discover site (if needed) and fetch all jobs.

    Launches one browser, navigates the careers page, optionally discovers
    the correct site name, calls the CXS API via ``page.evaluate``, and
    closes the browser — all in one session.

    Args:
        tenant: Workday tenant name.
        subdomain: Workday subdomain (e.g. ``"wd1"``).
        site: Career site name. If ``None``, attempt discovery.

    Returns:
        A list of raw job dicts, or ``None`` on failure.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not available")
        return None

    async def _run() -> list[dict[str, Any]] | None:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            discovered_site = site

            if not discovered_site:
                discovered_site = await _discover_site_on_page(page, tenant, subdomain)
                if not discovered_site:
                    logger.error("Could not discover career site for Workday %s/%s", subdomain, tenant)
                    await browser.close()
                    return None

            # Navigate to the correct careers page (if not already there).
            careers_url = _build_careers_url(tenant, subdomain, discovered_site)
            try:
                await page.goto(careers_url, timeout=30000, wait_until="networkidle")
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning("Playwright navigation to careers page failed for %s: %s", careers_url, e)
                await browser.close()
                return None

            jobs = await _fetch_jobs_on_page(page, tenant, subdomain, discovered_site)

            await browser.close()

            if jobs:
                logger.info("Fetched %d jobs from Workday %s/%s via Playwright", len(jobs), subdomain, tenant)
                return jobs

            logger.warning("No jobs returned for Workday %s/%s (site=%s)", subdomain, tenant, discovered_site)
            return None

    return asyncio.run(_run())


# ── Public API ───────────────────────────────────────────────────────────────


def fetch_jobs(
    tenant: str, subdomain: str, site: str | None = None, use_playwright: bool = False
) -> list[dict[str, Any]]:
    """Fetch all active jobs from a Workday tenant.

    Strategy:
    1. If *use_playwright* is ``True``, go directly to the single-session
       Playwright approach (site discovery + API calls in one browser).
    2. Otherwise try ``requests`` directly first, then fall back to Playwright.
    3. If site is unknown, attempt auto-discovery.

    Args:
        tenant: Workday tenant name.
        subdomain: Workday subdomain (e.g. ``"wd1"``, ``"wd5"``).
        site: Career site name. If ``None``, auto-discover.
        use_playwright: Skip ``requests`` path and go directly to Playwright.

    Returns:
        A list of raw job dicts (before ``_build_job_record`` normalisation).
    """
    if use_playwright:
        all_jobs = _fetch_workday_playwright(tenant, subdomain, site)
        if all_jobs is not None:
            return all_jobs
        logger.error("Playwright approach failed for Workday %s/%s", subdomain, tenant)
        return []

    if not site:
        site = _discover_site(tenant, subdomain)
        if not site:
            logger.error("Could not discover career site for Workday %s/%s", subdomain, tenant)
            return []

    data = _fetch_page_requests(tenant, subdomain, site, offset=0)
    if data is not None:
        job_postings = data.get("jobPostings")
        if isinstance(job_postings, list):
            all_jobs = list(job_postings)
            total = data.get("total") or 0
            offset = _PAGE_SIZE
            while offset < total:
                page_data = _fetch_page_requests(tenant, subdomain, site, offset=offset)
                if page_data is None:
                    break
                page_jobs = page_data.get("jobPostings") or []
                all_jobs.extend(page_jobs)
                offset += _PAGE_SIZE
            logger.info("Fetched %d jobs from Workday %s/%s via requests", len(all_jobs), subdomain, tenant)
            return all_jobs

    logger.info("Requests path failed for Workday %s/%s — trying Playwright", subdomain, tenant)
    all_jobs = _fetch_workday_playwright(tenant, subdomain, site)
    if all_jobs is not None:
        return all_jobs

    logger.error("All approaches failed for Workday %s/%s (site=%s)", subdomain, tenant, site)
    return []


class WorkdayCrawler(BaseCrawler):
    """Crawler for a specific company's Workday ATS."""

    platform = "workday"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        subdomain: str,
        tenant: str,
        site: str | None = None,
        locations: list[str] | None = None,
        use_playwright: bool = False,
    ) -> None:
        super().__init__(company_id, display_name, locations)
        self.subdomain = subdomain
        self.tenant = tenant
        self.site = site
        self.use_playwright = use_playwright

    def fetch_jobs(self) -> list[dict[str, Any]]:
        raw_jobs = fetch_jobs(self.tenant, self.subdomain, self.site, use_playwright=self.use_playwright)
        return [
            _build_job_record(job, self.display_name, self.tenant, self.subdomain, self.site or "") for job in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "WorkdayCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            subdomain=entry.get("subdomain", "wd1"),
            tenant=entry.get("tenant", entry["id"]),
            site=entry.get("site"),
            locations=entry.get("locations", []),
            use_playwright=entry.get("renderer") == "playwright",
        )
