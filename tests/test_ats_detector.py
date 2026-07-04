"""Unit tests for the ATS detection module."""

from crawlers.ats_detector import ATSDetectionResult, detect_ats


class TestATSDetector:
    """Test suite for detect_ats()."""

    def test_greenhouse_url_match(self):
        """Greenhouse URL should be detected with confidence 1.0."""
        result = detect_ats("https://boards.greenhouse.io/boschglobalsof")
        assert isinstance(result, ATSDetectionResult)
        assert result.ats_name == "greenhouse"
        assert result.confidence == 1.0
        assert result.reason == "url_pattern_match"

    def test_lever_url_match(self):
        """Lever URL should be detected with confidence 1.0."""
        result = detect_ats("https://jobs.lever.co/google")
        assert result.ats_name == "lever"
        assert result.confidence == 1.0

    def test_workday_url_match(self):
        """Workday URL should be detected with confidence 1.0."""
        result = detect_ats("https://myworkdayjobs.com/Company")
        assert result.ats_name == "workday"
        assert result.confidence == 1.0

    def test_ashby_url_match(self):
        """Ashby URL should be detected with confidence 1.0."""
        result = detect_ats("https://jobs.ashbyhq.com/company")
        assert result.ats_name == "ashby"
        assert result.confidence == 1.0

    def test_smartrecruiters_url_match(self):
        """SmartRecruiters URL should be detected with confidence 1.0."""
        result = detect_ats("https://www.smartrecruiters.com/Company")
        assert result.ats_name == "smartrecruiters"
        assert result.confidence == 1.0

    def test_no_match_without_html(self):
        """Unknown URL without HTML should return confidence 0.0."""
        result = detect_ats("https://example.com/careers")
        assert result.ats_name is None
        assert result.confidence == 0.0
        assert result.reason == "no_match"

    def test_meta_tag_detection(self):
        """HTML containing 'Greenhouse' should be detected with confidence 0.7."""
        html = "<html><head><title>Greenhouse Careers</title></head></html>"
        result = detect_ats("https://example.com/careers", page_html=html)
        assert result.ats_name == "greenhouse"
        assert result.confidence == 0.7
        assert result.reason == "meta_tag_detection"

    def test_meta_tag_detection_with_full_html(self):
        """HTML containing 'greenhouse' anywhere should be detected at 0.7."""
        html = "<html><body>Powered by greenhouse software</body></html>"
        result = detect_ats("https://example.com/careers", page_html=html)
        assert result.ats_name == "greenhouse"
        assert result.confidence == 0.7
        assert result.reason == "meta_tag_detection"

    def test_no_match_with_unrelated_html(self):
        """HTML with no ATS clues should return confidence 0.0."""
        html = "<html><body>Welcome to our careers page</body></html>"
        result = detect_ats("https://example.com/careers", page_html=html)
        assert result.ats_name is None
        assert result.confidence == 0.0

    def test_url_takes_priority_over_html(self):
        """URL match should be returned even if HTML also contains clues."""
        html = "<html><title>Greenhouse</title></html>"
        result = detect_ats("https://boards.greenhouse.io/acme", page_html=html)
        assert result.ats_name == "greenhouse"
        assert result.confidence == 1.0
        assert result.reason == "url_pattern_match"

    def test_case_insensitive_url(self):
        """URL matching should be case-insensitive."""
        result = detect_ats("HTTPS://BOARDS.GREENHOUSE.IO/ACME")
        assert result.ats_name == "greenhouse"
        assert result.confidence == 1.0
