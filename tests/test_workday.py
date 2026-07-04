"""Unit tests for the Workday crawler module."""

from typing import Any
from unittest.mock import patch

from crawlers.workday import WorkdayCrawler, _build_job_record, fetch_jobs

SAMPLE_WORKDAY_RESPONSE = {
    "total": 2,
    "jobPostings": [
        {
            "title": "Software Engineer II",
            "locationsText": "Bengaluru, India",
            "jobPostingId": "123456",
            "externalPath": "/Microsoft/job/123456/software-engineer-ii",
            "postedOnDate": "2026-07-01T12:00:00.000+0000",
            "categories": [{"name": "Engineering"}],
            "type": "Full-time",
            "description": {"text": "<p>Join our engineering team...</p>"},
        },
        {
            "title": "Data Scientist",
            "locationsText": "Hyderabad, India",
            "jobPostingId": "789012",
            "externalPath": "/Microsoft/job/789012/data-scientist",
            "postedOnDate": "2026-06-30T10:00:00.000+0000",
            "categories": [{"name": "Data & AI"}],
            "type": "Full-time",
            "description": {"text": "<p>Build ML models at scale...</p>"},
        },
    ],
}

SINGLE_JOB_RAW: dict[str, Any] = SAMPLE_WORKDAY_RESPONSE["jobPostings"][0]  # type: ignore[index]


class TestWorkdayBuildJobRecord:
    """Tests for _build_job_record()."""

    def test_build_record_has_all_fields(self):
        """The built record should contain all standard fields."""
        record = _build_job_record(SINGLE_JOB_RAW, "Microsoft", "Microsoft", "wd1", "Microsoft")
        assert record["title"] == "Software Engineer II"
        assert record["company"] == "Microsoft"
        assert record["location"] == "Bengaluru, India"
        assert record["description"] == ""
        assert (
            record["apply_url"] == "https://Microsoft.wd1.myworkdayjobs.com/Microsoft/job/123456/software-engineer-ii"
        )
        assert record["department"] == ""
        assert record["employment_type"] == ""
        assert record["source"] == "workday"
        assert record["source_id"] == "123456"

    def test_build_record_empty_categories(self):
        """A job with no categories should have empty department."""
        raw = {**SINGLE_JOB_RAW, "categories": []}
        record = _build_job_record(raw, "Microsoft", "Microsoft", "wd1", "Microsoft")
        assert record["department"] == ""

    def test_build_record_string_description(self):
        """A job with a plain string description should still work."""
        raw = {**SINGLE_JOB_RAW, "description": "<p>Plain string desc</p>"}
        record = _build_job_record(raw, "Microsoft", "Microsoft", "wd1", "Microsoft")
        assert record["description"] == ""

    def test_build_record_missing_external_path(self):
        """A job with no externalPath should have an empty apply_url."""
        raw = {**SINGLE_JOB_RAW, "externalPath": ""}
        record = _build_job_record(raw, "Microsoft", "Microsoft", "wd1", "Microsoft")
        assert record["apply_url"] == ""


class TestWorkdayFetchJobs:
    """Tests for fetch_jobs()."""

    @patch("crawlers.workday._fetch_page_requests")
    @patch("crawlers.workday._discover_site")
    def test_fetch_jobs_returns_parsed_list(self, mock_discover, mock_fetch):
        """fetch_jobs should return raw job dicts from the API response."""
        mock_discover.return_value = "Microsoft"
        mock_fetch.return_value = SAMPLE_WORKDAY_RESPONSE
        jobs = fetch_jobs("Microsoft", "wd1")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Software Engineer II"
        assert jobs[1]["title"] == "Data Scientist"

    @patch("crawlers.workday._fetch_page_requests")
    @patch("crawlers.workday._discover_site")
    def test_fetch_jobs_empty_response(self, mock_discover, mock_fetch):
        """An empty jobs list should return an empty list."""
        mock_discover.return_value = "Microsoft"
        mock_fetch.return_value = {"total": 0, "jobPostings": []}
        jobs = fetch_jobs("Empty", "wd1")
        assert jobs == []

    def test_fetch_jobs_no_site_returns_empty(self):
        """fetch_jobs should return empty list if site cannot be discovered."""
        jobs = fetch_jobs("Unknown", "wd1")
        assert jobs == []


class TestWorkdayCrawlerClass:
    """Tests for the WorkdayCrawler class."""

    def test_platform_classvar(self):
        """WorkdayCrawler.platform should be 'workday'."""
        assert WorkdayCrawler.platform == "workday"

    def test_constructor_sets_attributes(self):
        """The constructor should store all attributes."""
        crawler = WorkdayCrawler(
            company_id="microsoft",
            display_name="Microsoft",
            subdomain="wd1",
            tenant="Microsoft",
            locations=["Bengaluru", "Hyderabad"],
        )
        assert crawler.company_id == "microsoft"
        assert crawler.display_name == "Microsoft"
        assert crawler.subdomain == "wd1"
        assert crawler.tenant == "Microsoft"
        assert crawler.locations == ["Bengaluru", "Hyderabad"]
        assert crawler.site is None
        assert crawler.use_playwright is False

    @patch("crawlers.workday._fetch_page_requests")
    @patch("crawlers.workday._discover_site")
    def test_fetch_jobs_uses_display_name(self, mock_discover, mock_fetch):
        """The class fetch_jobs should set company to display_name."""
        mock_discover.return_value = "Microsoft"
        mock_fetch.return_value = SAMPLE_WORKDAY_RESPONSE
        crawler = WorkdayCrawler(
            company_id="microsoft",
            display_name="Microsoft",
            subdomain="wd1",
            tenant="Microsoft",
        )
        jobs = crawler.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["company"] == "Microsoft"
        assert jobs[0]["source"] == "workday"

    def test_from_registry_creates_crawler(self):
        """from_registry should create a WorkdayCrawler from a registry entry."""
        entry = {
            "id": "microsoft",
            "company": "Microsoft",
            "platform": "workday",
            "subdomain": "wd1",
            "tenant": "Microsoft",
            "enabled": True,
            "locations": ["Bengaluru"],
        }
        crawler = WorkdayCrawler.from_registry(entry)
        assert isinstance(crawler, WorkdayCrawler)
        assert crawler.company_id == "microsoft"
        assert crawler.display_name == "Microsoft"
        assert crawler.subdomain == "wd1"
        assert crawler.tenant == "Microsoft"
        assert crawler.locations == ["Bengaluru"]

    def test_from_registry_defaults_subdomain(self):
        """from_registry should default subdomain to 'wd1' if not specified."""
        entry = {
            "id": "test",
            "company": "Test",
            "platform": "workday",
            "tenant": "Test",
            "enabled": True,
            "locations": [],
        }
        crawler = WorkdayCrawler.from_registry(entry)
        assert crawler.subdomain == "wd1"
        assert crawler.tenant == "Test"

    def test_from_registry_sets_use_playwright(self):
        """from_registry should set use_playwright when renderer is playwright."""
        entry = {
            "id": "servicenow",
            "company": "ServiceNow",
            "platform": "workday",
            "subdomain": "wd1",
            "tenant": "ServiceNow",
            "renderer": "playwright",
            "enabled": True,
            "locations": [],
        }
        crawler = WorkdayCrawler.from_registry(entry)
        assert crawler.use_playwright is True

    def test_from_registry_sets_site(self):
        """from_registry should pass site from registry entry."""
        entry = {
            "id": "fractalan",
            "company": "Fractal Analytics",
            "platform": "workday",
            "subdomain": "wd1",
            "tenant": "Fractal",
            "site": "Careers",
            "renderer": "playwright",
            "enabled": True,
            "locations": [],
        }
        crawler = WorkdayCrawler.from_registry(entry)
        assert crawler.site == "Careers"
