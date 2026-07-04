"""Unit tests for the Workable crawler module."""

import responses

from crawlers.workable import WorkableCrawler, _build_job_record, fetch_jobs

SAMPLE_WORKABLE_RESPONSE = {
    "jobs": [
        {
            "title": "Software Engineer",
            "location": {"city": "Bengaluru", "country": "India"},
            "description": "<p>Build great software...</p>",
            "url": "https://apply.workable.com/tiger-analytics/j/12345",
            "department": "Engineering",
            "employment_type": "full-time",
            "published_date": "2026-07-01T12:00:00Z",
            "id": "12345",
            "shortcode": "abc123",
        },
        {
            "title": "Data Scientist",
            "location": "Remote",
            "description": "Data science role...",
            "apply_url": "https://apply.workable.com/tiger-analytics/j/67890",
            "department": "department:Data Science",
            "employment_type": "contract",
            "published_on": "2026-06-30T12:00:00Z",
            "shortcode": "def456",
        },
    ]
}

SINGLE_JOB_RAW = SAMPLE_WORKABLE_RESPONSE["jobs"][0]


class TestWorkableBuildJobRecord:
    """Test suite for _build_job_record()."""

    def test_build_record_has_all_fields(self):
        """The built record should contain all standard fields."""
        record = _build_job_record(SINGLE_JOB_RAW, "tiger-analytics")
        assert record["title"] == "Software Engineer"
        assert record["company"] == "tiger-analytics"
        assert record["location"] == "Bengaluru"
        assert record["description"] == "<p>Build great software...</p>"
        assert record["apply_url"] == "https://apply.workable.com/tiger-analytics/j/12345"
        assert record["department"] == "Engineering"
        assert record["employment_type"] == "Full-time"
        assert record["source"] == "workable"
        assert record["source_id"] == "12345"

    def test_build_record_string_location(self):
        """A job with a plain string location should use it directly."""
        raw = {**SINGLE_JOB_RAW, "location": "Remote, US"}
        record = _build_job_record(raw, "tiger-analytics")
        assert record["location"] == "Remote, US"

    def test_build_record_empty_location(self):
        """A job with no location should have empty string."""
        raw = {**SINGLE_JOB_RAW, "location": None}
        record = _build_job_record(raw, "tiger-analytics")
        assert record["location"] == ""

    def test_build_record_department_strips_prefix(self):
        """The department: prefix should be stripped."""
        raw = {**SINGLE_JOB_RAW, "department": "department:Data Science"}
        record = _build_job_record(raw, "tiger-analytics")
        assert record["department"] == "Data Science"

    def test_build_record_employment_type_map(self):
        """Employment types should be mapped to standard labels."""
        cases = [
            ("full-time", "Full-time"),
            ("part-time", "Part-time"),
            ("contract", "Contract"),
            ("temporary", "Temporary"),
            ("internship", "Intern"),
            ("freelance", "Freelance"),
            ("unknown", "unknown"),
        ]
        for raw_val, expected in cases:
            raw = {**SINGLE_JOB_RAW, "employment_type": raw_val}
            record = _build_job_record(raw, "tiger-analytics")
            assert record["employment_type"] == expected, f"failed for {raw_val}"


class TestWorkableFetchJobs:
    """Test suite for fetch_jobs()."""

    @responses.activate
    def test_fetch_jobs_returns_parsed_list(self):
        """fetch_jobs should return a list of parsed job records."""
        responses.get(
            "https://apply.workable.com/api/v1/widget/accounts/tiger-analytics?details=true",
            status=200,
            json=SAMPLE_WORKABLE_RESPONSE,
        )
        jobs = fetch_jobs("tiger-analytics")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[1]["title"] == "Data Scientist"

    @responses.activate
    def test_fetch_jobs_empty_response(self):
        """An empty jobs list should return an empty list."""
        responses.get(
            "https://apply.workable.com/api/v1/widget/accounts/empty?details=true",
            status=200,
            json={"jobs": []},
        )
        jobs = fetch_jobs("empty")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_api_error_returns_empty_list(self):
        """A failed API request should return an empty list."""
        responses.get(
            "https://apply.workable.com/api/v1/widget/accounts/unknown?details=true",
            status=500,
        )
        jobs = fetch_jobs("unknown")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_invalid_json_returns_empty_list(self):
        """Non-JSON response should return an empty list."""
        responses.get(
            "https://apply.workable.com/api/v1/widget/accounts/bad?details=true",
            status=200,
            body="<html>not json</html>",
        )
        jobs = fetch_jobs("bad")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_list_response(self):
        """Workable API may return a top-level list instead of dict."""
        responses.get(
            "https://apply.workable.com/api/v1/widget/accounts/listonly?details=true",
            status=200,
            json=SAMPLE_WORKABLE_RESPONSE["jobs"],
        )
        jobs = fetch_jobs("listonly")
        assert len(jobs) == 2

    @responses.activate
    def test_fetch_jobs_unexpected_format_returns_empty(self):
        """Unexpected response format should return an empty list."""
        responses.get(
            "https://apply.workable.com/api/v1/widget/accounts/weird?details=true",
            status=200,
            json={"not_jobs": "nope"},
        )
        jobs = fetch_jobs("weird")
        assert jobs == []


class TestWorkableCrawlerClass:
    """Tests for the WorkableCrawler class."""

    def test_platform_classvar(self):
        """WorkableCrawler.platform should be 'workable'."""
        assert WorkableCrawler.platform == "workable"

    def test_constructor_sets_attributes(self):
        """The constructor should store company_id, display_name, board_token, locations."""
        crawler = WorkableCrawler(
            company_id="tiger-analytics",
            display_name="Tiger Analytics",
            board_token="tiger-analytics",
            locations=["Bengaluru", "Chennai"],
        )
        assert crawler.company_id == "tiger-analytics"
        assert crawler.display_name == "Tiger Analytics"
        assert crawler.board_token == "tiger-analytics"
        assert crawler.locations == ["Bengaluru", "Chennai"]

    @responses.activate
    def test_fetch_jobs_uses_display_name_for_company(self):
        """The class fetch_jobs should set company to display_name not board_token."""
        responses.get(
            "https://apply.workable.com/api/v1/widget/accounts/tiger-analytics?details=true",
            status=200,
            json=SAMPLE_WORKABLE_RESPONSE,
        )
        crawler = WorkableCrawler(
            company_id="tiger-analytics",
            display_name="Tiger Analytics",
            board_token="tiger-analytics",
        )
        jobs = crawler.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["company"] == "Tiger Analytics"
        assert jobs[1]["company"] == "Tiger Analytics"
        assert jobs[0]["source"] == "workable"

    def test_from_registry_creates_crawler(self):
        """from_registry should create a WorkableCrawler from a registry entry."""
        entry = {
            "id": "tiger-analytics",
            "company": "Tiger Analytics",
            "platform": "workable",
            "board_token": "tiger-analytics",
            "enabled": True,
            "locations": ["Bengaluru"],
        }
        crawler = WorkableCrawler.from_registry(entry)
        assert isinstance(crawler, WorkableCrawler)
        assert crawler.company_id == "tiger-analytics"
        assert crawler.display_name == "Tiger Analytics"
        assert crawler.board_token == "tiger-analytics"
        assert crawler.locations == ["Bengaluru"]
