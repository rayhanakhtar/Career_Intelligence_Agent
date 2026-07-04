"""Tests for custom company-specific scrapers."""

from unittest.mock import patch

from crawlers.custom.amazon_careers import AmazonCrawler
from crawlers.custom.apple_careers import AppleCrawler
from crawlers.custom.cisco_careers import CiscoCrawler
from crawlers.custom.google_careers import GoogleCrawler
from crawlers.custom.ibm_careers import IbmCrawler
from crawlers.custom.intel_careers import IntelCrawler
from crawlers.custom.meta_careers import MetaCrawler
from crawlers.custom.nvidia_careers import NvidiaCrawler
from crawlers.custom.oracle_careers import OracleCrawler
from crawlers.custom.qualcomm_careers import QualcommCrawler

SAMPLE_HTML_WITH_JOBS = """
<html><body>
<div data-job-id="1">
  <h3><a href="/jobs/123">Software Engineer</a></h3>
  <span class="location">Bengaluru, India</span>
  <span class="job-category">Engineering</span>
  <time class="date">2026-07-01</time>
</div>
<div data-job-id="2">
  <h3><a href="/jobs/456">Data Scientist</a></h3>
  <span class="location">Hyderabad, India</span>
  <span class="job-category">Data & AI</span>
  <time class="date">2026-06-30</time>
</div>
</body></html>
"""

SAMPLE_HTML_NO_JOBS = "<html><body><p>No jobs found</p></body></html>"


class TestCustomScraperConstruction:
    """Tests that all custom scrapers can be constructed properly."""

    def test_google_construction(self):
        c = GoogleCrawler("google", "Google", ["Bengaluru"])
        assert c.company_id == "google"
        assert c.display_name == "Google"
        assert c.platform == "google_careers"

    def test_amazon_construction(self):
        c = AmazonCrawler("amazon", "Amazon", ["Bengaluru"])
        assert c.company_id == "amazon"
        assert c.platform == "amazon_careers"

    def test_meta_construction(self):
        c = MetaCrawler("meta", "Meta")
        assert c.company_id == "meta"
        assert c.platform == "meta_careers"

    def test_nvidia_construction(self):
        c = NvidiaCrawler("nvidia", "NVIDIA")
        assert c.platform == "nvidia_careers"

    def test_ibm_construction(self):
        c = IbmCrawler("ibm", "IBM")
        assert c.platform == "ibm_careers"

    def test_oracle_construction(self):
        c = OracleCrawler("oracle", "Oracle")
        assert c.platform == "oracle_careers"

    def test_cisco_construction(self):
        c = CiscoCrawler("cisco", "Cisco")
        assert c.platform == "cisco_careers"

    def test_intel_construction(self):
        c = IntelCrawler("intel", "Intel")
        assert c.platform == "intel_careers"

    def test_qualcomm_construction(self):
        c = QualcommCrawler("qualcomm", "Qualcomm")
        assert c.platform == "qualcomm_careers"

    def test_apple_construction(self):
        c = AppleCrawler("apple", "Apple")
        assert c.platform == "apple_careers"


class TestCustomScraperFromRegistry:
    """Tests for from_registry factory method."""

    def test_google_from_registry(self):
        entry = {
            "id": "google",
            "company": "Google",
            "platform": "google_careers",
            "enabled": True,
            "locations": ["Bengaluru"],
        }
        c = GoogleCrawler.from_registry(entry)
        assert isinstance(c, GoogleCrawler)
        assert c.company_id == "google"
        assert c.display_name == "Google"
        assert c.locations == ["Bengaluru"]

    def test_amazon_from_registry(self):
        entry = {"id": "amazon", "company": "Amazon", "platform": "amazon_careers", "enabled": True, "locations": []}
        c = AmazonCrawler.from_registry(entry)
        assert isinstance(c, AmazonCrawler)
        assert c.company_id == "amazon"

    def test_meta_from_registry(self):
        entry = {"id": "meta", "company": "Meta", "platform": "meta_careers", "enabled": True, "locations": []}
        c = MetaCrawler.from_registry(entry)
        assert isinstance(c, MetaCrawler)

    def test_nvidia_from_registry(self):
        entry = {"id": "nvidia", "company": "NVIDIA", "platform": "nvidia_careers", "enabled": True, "locations": []}
        c = NvidiaCrawler.from_registry(entry)
        assert isinstance(c, NvidiaCrawler)

    def test_ibm_from_registry(self):
        entry = {"id": "ibm", "company": "IBM", "platform": "ibm_careers", "enabled": True, "locations": []}
        c = IbmCrawler.from_registry(entry)
        assert isinstance(c, IbmCrawler)

    def test_oracle_from_registry(self):
        entry = {"id": "oracle", "company": "Oracle", "platform": "oracle_careers", "enabled": True, "locations": []}
        c = OracleCrawler.from_registry(entry)
        assert isinstance(c, OracleCrawler)

    def test_cisco_from_registry(self):
        entry = {"id": "cisco", "company": "Cisco", "platform": "cisco_careers", "enabled": True, "locations": []}
        c = CiscoCrawler.from_registry(entry)
        assert isinstance(c, CiscoCrawler)

    def test_intel_from_registry(self):
        entry = {"id": "intel", "company": "Intel", "platform": "intel_careers", "enabled": True, "locations": []}
        c = IntelCrawler.from_registry(entry)
        assert isinstance(c, IntelCrawler)

    def test_qualcomm_from_registry(self):
        entry = {
            "id": "qualcomm",
            "company": "Qualcomm",
            "platform": "qualcomm_careers",
            "enabled": True,
            "locations": [],
        }
        c = QualcommCrawler.from_registry(entry)
        assert isinstance(c, QualcommCrawler)

    def test_apple_from_registry(self):
        entry = {"id": "apple", "company": "Apple", "platform": "apple_careers", "enabled": True, "locations": []}
        c = AppleCrawler.from_registry(entry)
        assert isinstance(c, AppleCrawler)


class MockResponse:
    """Minimal mock for requests.Response."""

    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class TestAmazonCrawlerFetch:
    """Tests for AmazonCrawler.fetch_jobs."""

    @patch("crawlers.custom.amazon_careers.get_with_retry")
    def test_fetch_parses_jobs(self, mock_get):
        mock_get.return_value = MockResponse(SAMPLE_HTML_WITH_JOBS)
        crawler = AmazonCrawler("amazon", "Amazon")
        jobs = crawler.fetch_jobs()
        assert len(jobs) >= 1
        for j in jobs:
            assert j["company"] == "Amazon"
            assert j["source"] == "amazon_careers"

    @patch("crawlers.custom.amazon_careers.get_with_retry")
    def test_fetch_empty_html(self, mock_get):
        mock_get.return_value = MockResponse(SAMPLE_HTML_NO_JOBS)
        crawler = AmazonCrawler("amazon", "Amazon")
        jobs = crawler.fetch_jobs()
        assert jobs == []

    @patch("crawlers.custom.amazon_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = AmazonCrawler("amazon", "Amazon")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestGoogleCrawlerFetch:
    """Tests for GoogleCrawler.fetch_jobs."""

    @patch("crawlers.custom.google_careers.get_with_retry")
    def test_fetch_empty_on_no_ldjson(self, mock_get):
        mock_get.return_value = MockResponse("<html></html>")
        crawler = GoogleCrawler("google", "Google")
        jobs = crawler.fetch_jobs()
        assert jobs == []

    @patch("crawlers.custom.google_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = GoogleCrawler("google", "Google")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestMetaCrawlerFetch:
    """Tests for MetaCrawler.fetch_jobs."""

    @patch("crawlers.custom.meta_careers.get_with_retry")
    def test_fetch_empty_on_no_initial_state(self, mock_get):
        mock_get.return_value = MockResponse("<html></html>")
        crawler = MetaCrawler("meta", "Meta")
        jobs = crawler.fetch_jobs()
        assert jobs == []

    @patch("crawlers.custom.meta_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = MetaCrawler("meta", "Meta")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestNvidiaCrawlerFetch:
    """Tests for NvidiaCrawler.fetch_jobs."""

    @patch("crawlers.custom.nvidia_careers.get_with_retry")
    def test_fetch_parses_jobs(self, mock_get):
        mock_get.return_value = MockResponse(SAMPLE_HTML_WITH_JOBS)
        crawler = NvidiaCrawler("nvidia", "NVIDIA")
        jobs = crawler.fetch_jobs()
        assert len(jobs) >= 1
        for j in jobs:
            assert j["company"] == "NVIDIA"
            assert j["source"] == "nvidia_careers"

    @patch("crawlers.custom.nvidia_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = NvidiaCrawler("nvidia", "NVIDIA")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestIbmCrawlerFetch:
    """Tests for IbmCrawler.fetch_jobs."""

    @patch("crawlers.custom.ibm_careers.get_with_retry")
    def test_fetch_parses_jobs(self, mock_get):
        mock_get.return_value = MockResponse(SAMPLE_HTML_WITH_JOBS)
        crawler = IbmCrawler("ibm", "IBM")
        jobs = crawler.fetch_jobs()
        assert len(jobs) >= 1
        for j in jobs:
            assert j["company"] == "IBM"
            assert j["source"] == "ibm_careers"

    @patch("crawlers.custom.ibm_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = IbmCrawler("ibm", "IBM")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestOracleCrawlerFetch:
    """Tests for OracleCrawler.fetch_jobs."""

    @patch("crawlers.custom.oracle_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = OracleCrawler("oracle", "Oracle")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestCiscoCrawlerFetch:
    """Tests for CiscoCrawler.fetch_jobs."""

    @patch("crawlers.custom.cisco_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = CiscoCrawler("cisco", "Cisco")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestIntelCrawlerFetch:
    """Tests for IntelCrawler.fetch_jobs."""

    @patch("crawlers.custom.intel_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = IntelCrawler("intel", "Intel")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestQualcommCrawlerFetch:
    """Tests for QualcommCrawler.fetch_jobs."""

    @patch("crawlers.custom.qualcomm_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = QualcommCrawler("qualcomm", "Qualcomm")
        jobs = crawler.fetch_jobs()
        assert jobs == []


class TestAppleCrawlerFetch:
    """Tests for AppleCrawler.fetch_jobs."""

    @patch("crawlers.custom.apple_careers.get_with_retry")
    def test_fetch_empty_on_no_json(self, mock_get):
        mock_get.return_value = MockResponse("<html></html>")
        crawler = AppleCrawler("apple", "Apple")
        jobs = crawler.fetch_jobs()
        assert jobs == []

    @patch("crawlers.custom.apple_careers.get_with_retry")
    def test_fetch_failure(self, mock_get):
        mock_get.return_value = None
        crawler = AppleCrawler("apple", "Apple")
        jobs = crawler.fetch_jobs()
        assert jobs == []
