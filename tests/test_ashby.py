"""Unit tests for the Ashby crawler module."""

import responses

from crawlers.ashby import AshbyCrawler, _build_job_record, fetch_jobs

SAMPLE_ASHBY_RESPONSE = {
    "jobs": [
        {
            "title": "Software Engineer",
            "id": "abc-123",
            "applyUrl": "https://jobs.ashbyhq.com/sarvam/abc-123",
            "publishedAt": "2026-07-01T12:00:00Z",
            "location": "Bengaluru",
            "workplaceType": "On-site",
            "department": "Engineering",
            "employmentType": "FullTime",
            "descriptionHtml": "<p>Build great software...</p>",
            "isListed": True,
        },
        {
            "title": "Data Scientist",
            "id": "def-456",
            "jobUrl": "https://jobs.ashbyhq.com/sarvam/def-456",
            "publishedAt": "2026-06-30T12:00:00Z",
            "location": "Remote",
            "workplaceType": "Remote",
            "team": "Data & AI",
            "employmentType": "Contract",
            "descriptionPlain": "Data science role...",
            "isListed": True,
        },
    ]
}

SINGLE_JOB_RAW = SAMPLE_ASHBY_RESPONSE["jobs"][0]


class TestAshbyBuildJobRecord:
    """Test suite for _build_job_record()."""

    def test_build_record_has_all_fields(self):
        """The built record should contain all standard fields."""
        record = _build_job_record(SINGLE_JOB_RAW, "sarvam")
        assert record["title"] == "Software Engineer"
        assert record["company"] == "sarvam"
        assert record["location"] == "Bengaluru (On-site)"
        assert record["description"] == "<p>Build great software...</p>"
        assert record["apply_url"] == "https://jobs.ashbyhq.com/sarvam/abc-123"
        assert record["department"] == "Engineering"
        assert record["employment_type"] == "Full-time"
        assert record["source"] == "ashby"
        assert record["source_id"] == "abc-123"

    def test_build_record_workplace_type_only(self):
        """A job with no location but workplace type should use workplace type."""
        raw = {**SINGLE_JOB_RAW, "location": "", "workplaceType": "Remote"}
        record = _build_job_record(raw, "sarvam")
        assert record["location"] == "Remote"

    def test_build_record_no_location_no_workplace(self):
        """A job with no location or workplace type should have empty location."""
        raw = {**SINGLE_JOB_RAW, "location": "", "workplaceType": ""}
        record = _build_job_record(raw, "sarvam")
        assert record["location"] == ""

    def test_build_record_description_fallback(self):
        """descriptionPlain should be used when descriptionHtml is absent."""
        raw = {**SINGLE_JOB_RAW, "descriptionHtml": None, "descriptionPlain": "Plain text desc"}
        record = _build_job_record(raw, "sarvam")
        assert record["description"] == "Plain text desc"

    def test_build_record_employment_type_map(self):
        """Employment types should be mapped to standard labels."""
        cases = [
            ("FullTime", "Full-time"),
            ("PartTime", "Part-time"),
            ("Intern", "Intern"),
            ("Contract", "Contract"),
            ("Temporary", "Temporary"),
            ("UnknownType", "UnknownType"),
        ]
        for raw_val, expected in cases:
            raw = {**SINGLE_JOB_RAW, "employmentType": raw_val}
            record = _build_job_record(raw, "sarvam")
            assert record["employment_type"] == expected, f"failed for {raw_val}"

    def test_build_record_department_fallback(self):
        """department should fall back to team when department is missing."""
        raw = {**SINGLE_JOB_RAW, "department": None, "team": "Data & AI"}
        record = _build_job_record(raw, "sarvam")
        assert record["department"] == "Data & AI"


class TestAshbyFetchJobs:
    """Test suite for fetch_jobs()."""

    @responses.activate
    def test_fetch_jobs_returns_parsed_list(self):
        """fetch_jobs should return a list of parsed job records."""
        responses.get(
            "https://api.ashbyhq.com/posting-api/job-board/sarvam",
            status=200,
            json=SAMPLE_ASHBY_RESPONSE,
        )
        jobs = fetch_jobs("sarvam")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[1]["title"] == "Data Scientist"

    @responses.activate
    def test_fetch_jobs_empty_response(self):
        """An empty jobs list should return an empty list."""
        responses.get(
            "https://api.ashbyhq.com/posting-api/job-board/empty",
            status=200,
            json={"jobs": []},
        )
        jobs = fetch_jobs("empty")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_api_error_returns_empty_list(self):
        """A failed API request should return an empty list."""
        responses.get(
            "https://api.ashbyhq.com/posting-api/job-board/unknown",
            status=500,
        )
        jobs = fetch_jobs("unknown")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_invalid_json_returns_empty_list(self):
        """Non-JSON response should return an empty list."""
        responses.get(
            "https://api.ashbyhq.com/posting-api/job-board/bad",
            status=200,
            body="<html>not json</html>",
        )
        jobs = fetch_jobs("bad")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_filters_unlisted(self):
        """Jobs with isListed=False should be filtered out."""
        listed = {**SAMPLE_ASHBY_RESPONSE["jobs"][0], "isListed": False}
        responses.get(
            "https://api.ashbyhq.com/posting-api/job-board/unlisted",
            status=200,
            json={"jobs": SAMPLE_ASHBY_RESPONSE["jobs"] + [listed]},
        )
        jobs = fetch_jobs("unlisted")
        assert len(jobs) == 2

    @responses.activate
    def test_fetch_jobs_unexpected_format_returns_empty(self):
        """Unexpected response format should return an empty list."""
        responses.get(
            "https://api.ashbyhq.com/posting-api/job-board/weird",
            status=200,
            json={"not_jobs": "nope"},
        )
        jobs = fetch_jobs("weird")
        assert jobs == []


class TestAshbyCrawlerClass:
    """Tests for the AshbyCrawler class."""

    def test_platform_classvar(self):
        """AshbyCrawler.platform should be 'ashby'."""
        assert AshbyCrawler.platform == "ashby"

    def test_constructor_sets_attributes(self):
        """The constructor should store company_id, display_name, board_token, locations."""
        crawler = AshbyCrawler(
            company_id="sarvam",
            display_name="Sarvam AI",
            board_token="sarvam",
            locations=["Bengaluru"],
        )
        assert crawler.company_id == "sarvam"
        assert crawler.display_name == "Sarvam AI"
        assert crawler.board_token == "sarvam"
        assert crawler.locations == ["Bengaluru"]

    @responses.activate
    def test_fetch_jobs_uses_display_name_for_company(self):
        """The class fetch_jobs should set company to display_name not board_token."""
        responses.get(
            "https://api.ashbyhq.com/posting-api/job-board/sarvam",
            status=200,
            json=SAMPLE_ASHBY_RESPONSE,
        )
        crawler = AshbyCrawler(
            company_id="sarvam",
            display_name="Sarvam AI",
            board_token="sarvam",
        )
        jobs = crawler.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["company"] == "Sarvam AI"
        assert jobs[1]["company"] == "Sarvam AI"
        assert jobs[0]["source"] == "ashby"

    def test_from_registry_creates_crawler(self):
        """from_registry should create an AshbyCrawler from a registry entry."""
        entry = {
            "id": "sarvam",
            "company": "Sarvam AI",
            "platform": "ashby",
            "board_token": "sarvam",
            "enabled": True,
            "locations": ["Bengaluru"],
        }
        crawler = AshbyCrawler.from_registry(entry)
        assert isinstance(crawler, AshbyCrawler)
        assert crawler.company_id == "sarvam"
        assert crawler.display_name == "Sarvam AI"
        assert crawler.board_token == "sarvam"
        assert crawler.locations == ["Bengaluru"]
