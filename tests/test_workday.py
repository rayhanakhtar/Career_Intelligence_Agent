"""Unit tests for the Workday crawler module."""

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

SINGLE_JOB_RAW = SAMPLE_WORKDAY_RESPONSE["jobPostings"][0]


class TestWorkdayBuildJobRecord:
    """Tests for _build_job_record()."""

    def test_build_record_has_all_fields(self):
        """The built record should contain all standard fields."""
        record = _build_job_record(SINGLE_JOB_RAW, "Microsoft", "Microsoft", "wd1")
        assert record["title"] == "Software Engineer II"
        assert record["company"] == "Microsoft"
        assert record["location"] == "Bengaluru, India"
        assert record["description"] == "<p>Join our engineering team...</p>"
        assert record["apply_url"] == "https://wd1.myworkdayjobs.com/Microsoft/job/123456/software-engineer-ii"
        assert record["department"] == "Engineering"
        assert record["employment_type"] == "Full-time"
        assert record["source"] == "workday"
        assert record["source_id"] == "123456"

    def test_build_record_empty_categories(self):
        """A job with no categories should have empty department."""
        raw = {**SINGLE_JOB_RAW, "categories": []}
        record = _build_job_record(raw, "Microsoft", "Microsoft", "wd1")
        assert record["department"] == ""

    def test_build_record_string_description(self):
        """A job with a plain string description should still work."""
        raw = {**SINGLE_JOB_RAW, "description": "<p>Plain string desc</p>"}
        record = _build_job_record(raw, "Microsoft", "Microsoft", "wd1")
        assert record["description"] == "<p>Plain string desc</p>"

    def test_build_record_missing_external_path(self):
        """A job with no externalPath should have an empty apply_url."""
        raw = {**SINGLE_JOB_RAW, "externalPath": ""}
        record = _build_job_record(raw, "Microsoft", "Microsoft", "wd1")
        assert record["apply_url"] == ""


class TestWorkdayFetchJobs:
    """Tests for fetch_jobs()."""

    @patch("crawlers.workday._fetch_page")
    def test_fetch_jobs_returns_parsed_list(self, mock_fetch):
        """fetch_jobs should return a list of parsed job records."""
        mock_fetch.return_value = SAMPLE_WORKDAY_RESPONSE
        jobs = fetch_jobs("wd1", "Microsoft")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Software Engineer II"
        assert jobs[0]["company"] == "Microsoft"
        assert jobs[1]["title"] == "Data Scientist"
        assert jobs[1]["company"] == "Microsoft"

    @patch("crawlers.workday._fetch_page")
    def test_fetch_jobs_empty_response(self, mock_fetch):
        """An empty jobs list should return an empty list."""
        mock_fetch.return_value = {"total": 0, "jobPostings": []}
        jobs = fetch_jobs("wd1", "Empty")
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

    @patch("crawlers.workday._fetch_page")
    def test_fetch_jobs_uses_display_name(self, mock_fetch):
        """The class fetch_jobs should set company to display_name."""
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
