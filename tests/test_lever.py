"""Unit tests for the Lever crawler module."""

import responses

from crawlers.lever import (
    LeverCrawler,
    fetch_jobs,
    _build_job_record,
)


SAMPLE_LEVER_RESPONSE = [
    {
        "id": "abc-123",
        "text": "Machine Learning Engineer",
        "categories": {
            "location": "Electronic City, Bengaluru",
            "department": "Engineering",
            "commitment": "Full-time",
        },
        "description": "<p>Build ML models at scale...</p>",
        "hostedUrl": "https://jobs.lever.co/acme/abc-123",
        "createdAt": "2026-06-28T10:00:00Z",
    },
    {
        "id": "def-456",
        "text": "Data Science Intern",
        "categories": {
            "location": "Bengaluru",
            "department": "Data Science",
            "commitment": "Internship",
        },
        "description": "<p>Work on data pipelines...</p>",
        "hostedUrl": "https://jobs.lever.co/acme/def-456",
        "createdAt": "2026-06-29T10:00:00Z",
    },
]

SINGLE_JOB_RAW = SAMPLE_LEVER_RESPONSE[0]


class TestLeverBuildJobRecord:
    """Test suite for _build_job_record()."""

    def test_build_record_has_all_fields(self):
        """The built record should contain all standard fields."""
        record = _build_job_record(SINGLE_JOB_RAW, "acme")
        assert record["title"] == "Machine Learning Engineer"
        assert record["company"] == "acme"
        assert record["location"] == "Electronic City, Bengaluru"
        assert record["description"] == "<p>Build ML models at scale...</p>"
        assert record["apply_url"] == "https://jobs.lever.co/acme/abc-123"
        assert record["department"] == "Engineering"
        assert record["employment_type"] == "Full-time"
        assert record["source"] == "lever"
        assert record["source_id"] == "abc-123"

    def test_build_record_with_empty_categories(self):
        """A job with empty categories should not crash."""
        raw = {
            **SINGLE_JOB_RAW,
            "categories": {},
        }
        record = _build_job_record(raw, "acme")
        assert record["location"] == ""
        assert record["department"] == ""
        assert record["employment_type"] == ""


class TestLeverFetchJobs:
    """Test suite for fetch_jobs()."""

    @responses.activate
    def test_fetch_jobs_returns_parsed_list(self):
        """fetch_jobs should return a list of parsed job records."""
        responses.get(
            "https://api.lever.co/v0/postings/acme?mode=json",
            status=200,
            json=SAMPLE_LEVER_RESPONSE,
        )
        jobs = fetch_jobs("acme")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Machine Learning Engineer"
        assert jobs[1]["title"] == "Data Science Intern"

    @responses.activate
    def test_fetch_jobs_empty_response(self):
        """An empty array should return an empty list."""
        responses.get(
            "https://api.lever.co/v0/postings/empty?mode=json",
            status=200,
            json=[],
        )
        jobs = fetch_jobs("empty")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_api_error_returns_empty_list(self):
        """A failed API request should return an empty list."""
        responses.get(
            "https://api.lever.co/v0/postings/unknown?mode=json",
            status=500,
        )
        jobs = fetch_jobs("unknown")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_invalid_json_returns_empty_list(self):
        """Non-JSON response should return an empty list."""
        responses.get(
            "https://api.lever.co/v0/postings/bad?mode=json",
            status=200,
            body="not json",
        )
        jobs = fetch_jobs("bad")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_non_list_response_returns_empty_list(self):
        """A JSON object (not array) response should return an empty list."""
        responses.get(
            "https://api.lever.co/v0/postings/weird?mode=json",
            status=200,
            json={"error": "not an array"},
        )
        jobs = fetch_jobs("weird")
        assert jobs == []


class TestLeverCrawlerClass:
    """Tests for the LeverCrawler class."""

    def test_platform_classvar(self):
        """LeverCrawler.platform should be 'lever'."""
        assert LeverCrawler.platform == "lever"

    def test_constructor_sets_attributes(self):
        """The constructor should store company_id, display_name, board_token, locations."""
        crawler = LeverCrawler(
            company_id="acme",
            display_name="Acme Corp",
            board_token="acme",
            locations=["Bengaluru", "Mumbai"],
        )
        assert crawler.company_id == "acme"
        assert crawler.display_name == "Acme Corp"
        assert crawler.board_token == "acme"
        assert crawler.locations == ["Bengaluru", "Mumbai"]

    @responses.activate
    def test_fetch_jobs_uses_display_name_for_company(self):
        """The class fetch_jobs should set company to display_name not board_token."""
        responses.get(
            "https://api.lever.co/v0/postings/acme?mode=json",
            status=200,
            json=SAMPLE_LEVER_RESPONSE,
        )
        crawler = LeverCrawler(
            company_id="acme",
            display_name="Acme Corp",
            board_token="acme",
        )
        jobs = crawler.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["company"] == "Acme Corp"
        assert jobs[1]["company"] == "Acme Corp"
        assert jobs[0]["source"] == "lever"

    def test_from_registry_creates_crawler(self):
        """from_registry should create a LeverCrawler from a registry entry."""
        entry = {
            "id": "acme",
            "company": "Acme Corp",
            "platform": "lever",
            "board_token": "acme",
            "enabled": True,
            "locations": ["Bengaluru"],
        }
        crawler = LeverCrawler.from_registry(entry)
        assert isinstance(crawler, LeverCrawler)
        assert crawler.company_id == "acme"
        assert crawler.display_name == "Acme Corp"
        assert crawler.board_token == "acme"
        assert crawler.locations == ["Bengaluru"]
