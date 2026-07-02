"""Unit tests for the HTTP utilities module."""

import pytest
import requests
import responses

from crawlers.utils import get_with_retry


class TestGetWithRetry:
    """Test suite for get_with_retry()."""

    @responses.activate
    def test_successful_request(self):
        """A successful GET should return the response."""
        responses.get("https://example.com/jobs", status=200, json=[{"id": 1}])
        result = get_with_retry("https://example.com/jobs", max_retries=1)
        assert result is not None
        assert result.status_code == 200
        assert result.json() == [{"id": 1}]

    @responses.activate
    def test_retry_on_500_then_success(self):
        """A 500 error followed by success on retry should return the response."""
        responses.get(
            "https://example.com/jobs",
            status=500,
            body="Server Error",
        )
        responses.get(
            "https://example.com/jobs",
            status=200,
            json=[{"id": 1}],
        )
        result = get_with_retry("https://example.com/jobs", max_retries=2, delay=0)
        assert result is not None
        assert result.status_code == 200

    @responses.activate
    def test_exhaust_retries_on_500(self):
        """Repeated 500 errors should return None after exhausting retries."""
        for _ in range(3):
            responses.get("https://example.com/jobs", status=500, body="Server Error")

        result = get_with_retry("https://example.com/jobs", max_retries=2, delay=0)
        assert result is None

    @responses.activate
    def test_404_returns_none_immediately(self):
        """A 404 should not be retried and should return None."""
        responses.get("https://example.com/jobs", status=404)
        result = get_with_retry("https://example.com/jobs", max_retries=3, delay=0)
        assert result is None

    @responses.activate
    def test_retry_on_429(self):
        """A 429 (rate limit) should be retried."""
        responses.get("https://example.com/jobs", status=429, body="Too Many Requests")
        responses.get("https://example.com/jobs", status=200, json=[{"id": 1}])

        result = get_with_retry("https://example.com/jobs", max_retries=2, delay=0)
        assert result is not None
        assert result.status_code == 200

    @responses.activate
    def test_connection_error_returns_none(self):
        """A connection error should return None after retries."""
        responses.get("https://example.com/jobs", body=requests.exceptions.ConnectionError())
        responses.get("https://example.com/jobs", body=requests.exceptions.ConnectionError())

        result = get_with_retry("https://example.com/jobs", max_retries=1, delay=0)
        assert result is None

    @responses.activate
    def test_invalid_url_returns_none(self):
        """An invalid URL should return None without crashing."""
        result = get_with_retry("not-a-valid-url", max_retries=1, delay=0)
        assert result is None
