"""Crawler for Workday ATS via hybrid Playwright+requests approach.

Strategy (in order):
1. Try ``requests`` directly (fast path — some tenants bypass WAF).
2. On failure (422/406/403), use Playwright to load the careers page,
   extract Cloudflare/Workday cookies, then use ``requests.Session``
   with those cookies for paginated API calls.
3. If the CXS API still fails, attempt to parse job data from the
   rendered Playwright page HTML.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any

import requests

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

_PAGE_SIZE = 200
_MAX_PAGE_RETRIES = 3

# Common career site name patterns tried for each tenant.
_SITE_PATTERNS = [
    "{tenant}ExternalCareerSite",
    "External",
    "{tenant}",
    "Careers",
    f"External_Career_Site",
]


def _build_workday_host(tenant: str, subdomain: str) -> str:
    """Build the correct Workday hostname.

    Correct format: ``{tenant}.{subdomain}.myworkdayjobs.com``
    Old (broken) format: ``{subdomain}.myworkdayjobs.com``
    """
    return f"{tenant}.{subdomain}.myworkdayjobs.com"


def _build_api_url(tenant: str, subdomain: str, site: str) -> str:
    """Build the CXS jobs API URL.

    Correct format::
        https://{tenant}.{subdomain}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
    """
    host = _build_workday_host(tenant, subdomain)
    return f"https://{host}/wday/cxs/{tenant}/{site}/jobs"


def _build_careers_url(tenant: str, subdomain: str, site: str | None = None) -> str:
    """Build the public career page URL for a Workday tenant."""
    host = _build_workday_host(tenant, subdomain)
    if site:
        return f"https://{host}/{site}"
    return f"https://{host}/"


def _fetch_page_requests(
    tenant: str, subdomain: str, site: str, offset: int = 0, limit: int = _PAGE_SIZE,
    session: requests.Session | None = None,
) -> dict[str, Any] | None:
    """Fetch a single page of jobs via ``requests``.

    Args:
        tenant: Workday tenant name.
        subdomain: Workday subdomain (e.g. ``"wd1"``).
        site: Career site name (e.g. ``"NvidiaExternalCareerSite"``).
        offset: Pagination offset.
        limit: Page size.
        session: Optional ``requests.Session`` (for cookie injection).

    Returns:
        Parsed JSON response, or ``None`` on failure.
    """
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
                    attempt - 1, _MAX_PAGE_RETRIES, subdomain, tenant, site, offset, backoff,
                )
                time.sleep(backoff)

            response = sess.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning("Timeout on Workday %s/%s (site=%s) offset=%d (attempt %d/%d)", subdomain, tenant, site, offset, attempt, _MAX_PAGE_RETRIES)
        except requests.exceptions.HTTPError as e:
            last_error = e
            status = e.response.status_code if e.response is not None else 0
            logger.warning("HTTP %d on Workday %s/%s (site=%s) offset=%d (attempt %d/%d)", status, subdomain, tenant, site, offset, attempt, _MAX_PAGE_RETRIES)
            if status in (401, 403, 406, 422):
                return None
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning("Request failed for Workday %s/%s offset=%d: %s", subdomain, tenant, offset, e)

    logger.error("All retries exhausted for Workday %s/%s offset=%d: %s", subdomain, tenant, offset, last_error)
    return None


def _discover_site(
    tenant: str, subdomain: str,
) -> str | None:
    """Try to discover the correct career site name for a Workday tenant.

    Tries common patterns first, then falls back to a Playwright
    page load that intercepts the SPA's own API call.

    Returns:
        The discovered site name, or ``None`` if not found.
    """
    # Try common patterns via direct requests first.
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

    logger.info("Site discovery via patterns failed for %s/%s — will try Playwright fallback", subdomain, tenant)
    return None


def _build_job_record(job: dict[str, Any], display_name: str, tenant: str, subdomain: str, site: str) -> dict[str, Any]:
    """Normalise a raw Workday job dict into the standard job record format."""
    ext_path = job.get("externalPath") or ""
    if ext_path.startswith("/"):
        host = _build_workday_host(tenant, subdomain)
        apply_url = f"https://{host}{ext_path}"
    else:
        apply_url = ""

    # Extract job ID from bulletFields or other fields.
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


def _fetch_with_playwright_evaluate(
    tenant: str, subdomain: str, site: str,
) -> list[dict[str, Any]] | None:
    """Use Playwright to load the careers page, then call CXS API via browser
    ``fetch`` inside ``page.evaluate``.

    This avoids HTTP 400 errors caused by TLS fingerprinting differences
    between ``requests`` and a real browser — even when the same cookies
    are forwarded.

    Returns:
        A list of raw job dicts, or ``None`` on failure.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not available — cannot use evaluate approach")
        return None

    async def _run() -> list[dict[str, Any]] | None:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            careers_url = _build_careers_url(tenant, subdomain, site)
            api_url = _build_api_url(tenant, subdomain, site)
            logger.info("Playwright evaluate: loading %s", careers_url)

            try:
                await page.goto(careers_url, timeout=60000, wait_until="networkidle")
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning("Playwright navigation failed for %s: %s", careers_url, e)
                await browser.close()
                return None

            # Call the CXS API from inside the browser context using native fetch.
            # This automatically sends cookies and passes Cloudflare/TLS checks.
            script = f"""
                (async () => {{
                    const allJobs = [];
                    let offset = 0;
                    let total = Infinity;
                    const pageSize = {json.dumps(_PAGE_SIZE)};
                    const apiUrl = {json.dumps(api_url)};

                    while (offset < total) {{
                        try {{
                            const resp = await fetch(apiUrl, {{
                                method: "POST",
                                headers: {{
                                    "Content-Type": "application/json",
                                    "Accept": "application/json"
                                }},
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
                    logger.info(
                        "Fetched %d jobs from Workday %s/%s via Playwright evaluate",
                        len(all_jobs), subdomain, tenant,
                    )
                    await browser.close()
                    return all_jobs
                logger.warning(
                    "No jobs returned from page.evaluate for %s/%s (got %s)",
                    subdomain, tenant, type(all_jobs).__name__,
                )
            except Exception as e:
                logger.warning("page.evaluate failed for %s/%s: %s", subdomain, tenant, e)

            await browser.close()
            return None

    return asyncio.run(_run())


def _discover_site_playwright(
    tenant: str, subdomain: str,
) -> str | None:
    """Discover the career site name for a Workday tenant using Playwright.

    Navigates to the base careers hostname and intercepts API calls made
    by the SPA to sniff the correct ``site`` path segment.

    Returns:
        The discovered site name, or ``None`` if not found.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not available — cannot discover site")
        return None

    discovered: str | None = None

    async def _run() -> str | None:
        nonlocal discovered
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Intercept API calls to extract site name from URL path.
            async def _on_response(response):
                nonlocal discovered
                if discovered is not None:
                    return
                url = response.url
                match = re.search(rf"/wday/cxs/{re.escape(tenant)}/([^/]+)/jobs", url)
                if match:
                    discovered = match.group(1)

            page.on("response", _on_response)

            # Try the base domain first (may redirect to a site).
            base_url = f"https://{tenant}.{subdomain}.myworkdayjobs.com/"
            try:
                await page.goto(base_url, timeout=30000, wait_until="networkidle")
                await asyncio.sleep(5)
            except Exception:
                pass

            if discovered:
                logger.info("Discovered Workday site '%s' for %s/%s via Playwright (base)", discovered, subdomain, tenant)
                await browser.close()
                return discovered

            # Try common patterns by navigating directly.
            for pattern in _SITE_PATTERNS:
                site = pattern.format(tenant=tenant)
                url = f"https://{tenant}.{subdomain}.myworkdayjobs.com/{site}"
                try:
                    await page.goto(url, timeout=30000, wait_until="networkidle")
                    await asyncio.sleep(5)
                    if discovered:
                        logger.info("Discovered Workday site '%s' for %s/%s via Playwright (pattern: %s)", discovered, subdomain, tenant, pattern)
                        await browser.close()
                        return discovered
                except Exception:
                    continue

            logger.info("Site discovery via Playwright failed for %s/%s — tried %d patterns", subdomain, tenant, len(_SITE_PATTERNS))
            await browser.close()
            return None

    return asyncio.run(_run())


def fetch_jobs(tenant: str, subdomain: str, site: str | None = None, use_playwright: bool = False) -> list[dict[str, Any]]:
    """Fetch all active jobs from a Workday tenant.

    Strategy:
    1. If *use_playwright* is ``True``, try Playwright-based site discovery
       then call the CXS API via ``page.evaluate`` (browser ``fetch``).
    2. Otherwise try ``requests`` directly first, then fall back to Playwright.
    3. If site is unknown, attempt auto-discovery (requests patterns first,
       then Playwright-based intercept if available).

    Args:
        tenant: Workday tenant name.
        subdomain: Workday subdomain (e.g. ``"wd1"``, ``"wd5"``).
        site: Career site name. If ``None``, auto-discover.
        use_playwright: Skip ``requests`` path and go directly to Playwright
            ``page.evaluate`` approach.

    Returns:
        A list of raw job dicts (before ``_build_job_record`` normalisation).
    """
    # Auto-discover site if not provided.
    if not site:
        if use_playwright:
            site = _discover_site_playwright(tenant, subdomain)
        else:
            site = _discover_site(tenant, subdomain)
        if not site:
            logger.error("Could not discover career site for Workday %s/%s", subdomain, tenant)
            return []

    if use_playwright:
        all_jobs = _fetch_with_playwright_evaluate(tenant, subdomain, site)
        if all_jobs is not None:
            return all_jobs
        logger.error("Playwright evaluate approach failed for Workday %s/%s (site=%s)", subdomain, tenant, site)
        return []

    # Fast path: try requests directly.
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

    # Fallback: try Playwright evaluate approach.
    logger.info("Requests path failed for Workday %s/%s — trying Playwright evaluate", subdomain, tenant)
    all_jobs = _fetch_with_playwright_evaluate(tenant, subdomain, site)
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
            _build_job_record(job, self.display_name, self.tenant, self.subdomain, self.site or "")
            for job in raw_jobs
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
