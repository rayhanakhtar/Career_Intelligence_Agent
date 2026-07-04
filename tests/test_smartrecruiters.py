"""Unit tests for the SmartRecruiters crawler module."""

from typing import Any

import responses

from crawlers.smartrecruiters import SmartRecruitersCrawler, _build_job_record, fetch_jobs

SAMPLE_SMARTRECRUITERS_RESPONSE = {
    "totalFound": 2,
    "content": [
        {
            "name": "Software Engineer",
            "uuid": "abc-123",
            "ref": "https://careers.smartrecruiters.com/FractalAnalytics/abc-123",
            "releasedDate": "2026-07-01T12:00:00Z",
            "location": {"city": "Bengaluru", "region": "Karnataka", "country": "India"},
            "department": {"label": "Engineering"},
            "type": {"label": "Full-time"},
        },
        {
            "name": "Data Scientist",
            "uuid": "def-456",
            "ref": "https://careers.smartrecruiters.com/FractalAnalytics/def-456",
            "releasedDate": "2026-06-30T12:00:00Z",
            "location": {"city": "Mumbai", "country": "India"},
            "type": {"label": "Contract"},
        },
    ],
}

SINGLE_JOB_RAW: dict[str, Any] = SAMPLE_SMARTRECRUITERS_RESPONSE["content"][0]  # type: ignore[index]


class TestSmartRecruitersBuildJobRecord:
    """Test suite for _build_job_record()."""

    def test_build_record_has_all_fields(self):
        """The built record should contain all standard fields."""
        record = _build_job_record(SINGLE_JOB_RAW, "FractalAnalytics")
        assert record["title"] == "Software Engineer"
        assert record["company"] == "FractalAnalytics"
        assert record["location"] == "Bengaluru, Karnataka, India"
        assert record["description"] == ""
        assert record["apply_url"] == "https://careers.smartrecruiters.com/FractalAnalytics/abc-123"
        assert record["department"] == "Engineering"
        assert record["employment_type"] == "Full-time"
        assert record["source"] == "smartrecruiters"
        assert record["source_id"] == "abc-123"

    def test_build_record_minimal_location(self):
        """A job with only city and country should still produce a valid location."""
        raw = {**SINGLE_JOB_RAW, "location": {"city": "Mumbai", "country": "India"}}
        record = _build_job_record(raw, "FractalAnalytics")
        assert record["location"] == "Mumbai, India"

    def test_build_record_no_location(self):
        """A job with no location data should have empty location string."""
        raw = {**SINGLE_JOB_RAW, "location": None}
        record = _build_job_record(raw, "FractalAnalytics")
        assert record["location"] == ""

    def test_build_record_no_department(self):
        """A job with no department should have empty department string."""
        raw = {**SINGLE_JOB_RAW, "department": None}
        record = _build_job_record(raw, "FractalAnalytics")
        assert record["department"] == ""


class TestSmartRecruitersFetchJobs:
    """Test suite for fetch_jobs()."""

    @responses.activate
    def test_fetch_jobs_returns_parsed_list(self):
        """fetch_jobs should return a list of parsed job records."""
        responses.get(
            "https://api.smartrecruiters.com/v1/companies/FractalAnalytics/postings?limit=100&offset=0",
            status=200,
            json=SAMPLE_SMARTRECRUITERS_RESPONSE,
        )
        jobs = fetch_jobs("FractalAnalytics")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[1]["title"] == "Data Scientist"

    @responses.activate
    def test_fetch_jobs_empty_response(self):
        """An empty jobs list should return an empty list."""
        responses.get(
            "https://api.smartrecruiters.com/v1/companies/empty/postings?limit=100&offset=0",
            status=200,
            json={"totalFound": 0, "content": []},
        )
        jobs = fetch_jobs("empty")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_api_error_returns_empty_list(self):
        """A failed API request should return an empty list."""
        responses.get(
            "https://api.smartrecruiters.com/v1/companies/unknown/postings?limit=100&offset=0",
            status=500,
        )
        jobs = fetch_jobs("unknown")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_invalid_json_returns_empty_list(self):
        """Non-JSON response should return an empty list."""
        responses.get(
            "https://api.smartrecruiters.com/v1/companies/bad/postings?limit=100&offset=0",
            status=200,
            body="<html>not json</html>",
        )
        jobs = fetch_jobs("bad")
        assert jobs == []

    @responses.activate
    def test_fetch_jobs_pagination_multiple_pages(self):
        """fetch_jobs should paginate through multiple pages."""
        page1 = {"totalFound": 3, "content": [SAMPLE_SMARTRECRUITERS_RESPONSE["content"][0]]}
        page2 = {"totalFound": 3, "content": [SAMPLE_SMARTRECRUITERS_RESPONSE["content"][1]]}
        responses.get(
            "https://api.smartrecruiters.com/v1/companies/multi/postings?limit=100&offset=0",
            status=200,
            json=page1,
        )
        responses.get(
            "https://api.smartrecruiters.com/v1/companies/multi/postings?limit=100&offset=1",
            status=200,
            json=page2,
        )
        jobs = fetch_jobs("multi")
        assert len(jobs) == 2


class TestSmartRecruitersCrawlerClass:
    """Tests for the SmartRecruitersCrawler class."""

    def test_platform_classvar(self):
        """SmartRecruitersCrawler.platform should be 'smartrecruiters'."""
        assert SmartRecruitersCrawler.platform == "smartrecruiters"

    def test_constructor_sets_attributes(self):
        """The constructor should store company_id, display_name, board_token, locations."""
        crawler = SmartRecruitersCrawler(
            company_id="fractal",
            display_name="Fractal Analytics",
            board_token="FractalAnalytics",
            locations=["Bengaluru", "Mumbai"],
        )
        assert crawler.company_id == "fractal"
        assert crawler.display_name == "Fractal Analytics"
        assert crawler.board_token == "FractalAnalytics"
        assert crawler.locations == ["Bengaluru", "Mumbai"]

    @responses.activate
    def test_fetch_jobs_uses_display_name_for_company(self):
        """The class fetch_jobs should set company to display_name not board_token."""
        responses.get(
            "https://api.smartrecruiters.com/v1/companies/FractalAnalytics/postings?limit=100&offset=0",
            status=200,
            json=SAMPLE_SMARTRECRUITERS_RESPONSE,
        )
        crawler = SmartRecruitersCrawler(
            company_id="fractal",
            display_name="Fractal Analytics",
            board_token="FractalAnalytics",
        )
        jobs = crawler.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["company"] == "Fractal Analytics"
        assert jobs[1]["company"] == "Fractal Analytics"
        assert jobs[0]["source"] == "smartrecruiters"

    def test_from_registry_creates_crawler(self):
        """from_registry should create a SmartRecruitersCrawler from a registry entry."""
        entry = {
            "id": "fractal",
            "company": "Fractal Analytics",
            "platform": "smartrecruiters",
            "board_token": "FractalAnalytics",
            "enabled": True,
            "locations": ["Bengaluru"],
        }
        crawler = SmartRecruitersCrawler.from_registry(entry)
        assert isinstance(crawler, SmartRecruitersCrawler)
        assert crawler.company_id == "fractal"
        assert crawler.display_name == "Fractal Analytics"
        assert crawler.board_token == "FractalAnalytics"
        assert crawler.locations == ["Bengaluru"]
