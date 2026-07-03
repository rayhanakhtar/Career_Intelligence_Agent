"""Unit tests for the Greenhouse crawler module."""

import json
import responses

from crawlers.greenhouse import (
    GreenhouseCrawler,
    fetch_jobs,
    _build_job_record,
)


SAMPLE_GREENHOUSE_RESPONSE = {
    "jobs": [
        {
            "id": 12345,
            "title": "AI/ML Engineer Intern",
            "location": {"name": "Electronic City, Bengaluru"},
            "content": "<p>Work on machine learning models...</p>",
            "absolute_url": "https://boards.greenhouse.io/boschglobalsof/jobs/12345",
            "updated_at": "2026-07-01T12:00:00Z",
            "departments": [{"name": "Engineering"}],
            "metadata": [
                {"id": 1, "value": "Internship"},
                {"id": 2, "value": "0-1 years"},
            ],
        },
        {
            "id": 12346,
            "title": "Data Scientist",
            "location": {"name": "Bengaluru, India"},
            "content": "<p>Data science role in AI team...</p>",
            "absolute_url": "https://boards.greenhouse.io/boschglobalsof/jobs/12346",
            "updated_at": "2026-06-30T12:00:00Z",
            "departments": [{"name": "Data Science"}],
            "metadata": [
                {"id": 1, "value": "Full-time"},
            ],
        },
    ]
}

SINGLE_JOB_RAW = SAMPLE_GREENHOUSE_RESPONSE["jobs"][0]


class TestGreenhouseBuildJobRecord:
    """Test suite for _build_job_record()."""

    def test_build_record_has_all_fields(self):
        """The built record should contain all standard fields."""
        record = _build_job_record(SINGLE_JOB_RAW, "boschglobalsof")
        assert record["title"] == "AI/ML Engineer Intern"
        assert record["company"] == "boschglobalsof"
        assert record["location"] == "Electronic City, Bengaluru"
        assert record["description"] == "<p>Work on machine learning models...</p>"
        assert record["apply_url"] == "https://boards.greenhouse.io/boschglobalsof/jobs/12345"
        assert record["department"] == "Engineering"
        assert record["employment_type"] == "Internship"
        assert record["source"] == "greenhouse"
        assert record["source_id"] == "12345"

    def test_build_record_with_empty_metadata(self):
        """A job with no metadata should not crash."""
        raw = {**SINGLE_JOB_RAW, "metadata": []}
        record = _build_job_record(raw, "boschglobalsof")
        assert record["employment_type"] == ""
        assert record["title"] == "AI/ML Engineer Intern"

    def test_build_record_with_no_departments(self):
        """A job with no departments should have empty department string."""
        raw = {**SINGLE_JOB_RAW, "departments": []}
        record = _build_job_record(raw, "boschglobalsof")
        assert record["department"] == ""


class TestGreenhouseFetchJobs:
    """Test suite for fetch_jobs()."""

    @responses.activate
    def test_fetch_jobs_returns_parsed_list(self):
        """fetch_jobs should return a list of parsed job records."""
        responses.get(
            "https://boards-api.greenhouse.io/v1/boards/boschglobalsof/jobs",
            status=200,
            json=SAMPLE_GREENHOUSE_RESPONSE,
        )
        jobs = fetch_jobs("boschglobalsof")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "AI/ML Engineer Intern"
        assert jobs[1]["title"] == "Data Scientist"

    @responses.activate
    def test_fetch_jobs_empty_response(self):
        """An empty jobs list should return an empty list."""
        responses.get(
            "https://boards-api.greenhouse.io/v1/boards/empty/jobs",
            status=200,
            json={"jobs": []},
        )
        jobs = fetch_jobs("empty")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_api_error_returns_empty_list(self):
        """A failed API request should return an empty list."""
        responses.get(
            "https://boards-api.greenhouse.io/v1/boards/unknown/jobs",
            status=500,
        )
        jobs = fetch_jobs("unknown")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_invalid_json_returns_empty_list(self):
        """Non-JSON response should return an empty list."""
        responses.get(
            "https://boards-api.greenhouse.io/v1/boards/bad/jobs",
            status=200,
            body="<html>not json</html>",
        )
        jobs = fetch_jobs("bad")
        assert jobs == []


class TestGreenhouseCrawlerClass:
    """Tests for the GreenhouseCrawler class."""

    def test_platform_classvar(self):
        """GreenhouseCrawler.platform should be 'greenhouse'."""
        assert GreenhouseCrawler.platform == "greenhouse"

    def test_constructor_sets_attributes(self):
        """The constructor should store company_id, display_name, board_token, locations."""
        crawler = GreenhouseCrawler(
            company_id="bosch",
            display_name="Bosch",
            board_token="boschglobalsof",
            locations=["Bengaluru", "Electronic City"],
        )
        assert crawler.company_id == "bosch"
        assert crawler.display_name == "Bosch"
        assert crawler.board_token == "boschglobalsof"
        assert crawler.locations == ["Bengaluru", "Electronic City"]

    @responses.activate
    def test_fetch_jobs_uses_display_name_for_company(self):
        """The class fetch_jobs should set company to display_name not board_token."""
        responses.get(
            "https://boards-api.greenhouse.io/v1/boards/boschglobalsof/jobs",
            status=200,
            json=SAMPLE_GREENHOUSE_RESPONSE,
        )
        crawler = GreenhouseCrawler(
            company_id="bosch",
            display_name="Bosch",
            board_token="boschglobalsof",
        )
        jobs = crawler.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["company"] == "Bosch"
        assert jobs[1]["company"] == "Bosch"
        assert jobs[0]["source"] == "greenhouse"

    def test_from_registry_creates_crawler(self):
        """from_registry should create a GreenhouseCrawler from a registry entry."""
        entry = {
            "id": "bosch",
            "company": "Bosch",
            "platform": "greenhouse",
            "board_token": "boschglobalsof",
            "enabled": True,
            "locations": ["Bengaluru"],
        }
        crawler = GreenhouseCrawler.from_registry(entry)
        assert isinstance(crawler, GreenhouseCrawler)
        assert crawler.company_id == "bosch"
        assert crawler.display_name == "Bosch"
        assert crawler.board_token == "boschglobalsof"
        assert crawler.locations == ["Bengaluru"]
