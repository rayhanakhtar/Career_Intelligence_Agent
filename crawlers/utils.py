"""Shared HTTP utilities for crawling career pages."""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_FACTOR = 0.5


def _build_session(max_retries: int = _DEFAULT_MAX_RETRIES) -> requests.Session:
    """Build a requests Session with retry and backoff configuration.

    Args:
        max_retries: Maximum number of retry attempts for failed requests.

    Returns:
        Configured requests.Session instance.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=_DEFAULT_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def get_with_retry(
    url: str,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    timeout: int = _DEFAULT_TIMEOUT,
    delay: float = 1.0,
) -> requests.Response | None:
    """Perform a GET request with retry logic and polite delay.

    Uses urllib3 Retry for transient failures (429, 5xx), plus an additional
    time.sleep(delay) before each attempt for simple rate limiting.

    Args:
        url: The URL to fetch.
        max_retries: Maximum number of retry attempts.
        timeout: Request timeout in seconds.
        delay: Fixed delay in seconds between retry attempts (polite crawling).

    Returns:
        A requests.Response on success, or None if all retries are exhausted.
    """
    session = _build_session(max_retries=max_retries)

    for attempt in range(1, max_retries + 2):  # +1 for the initial attempt
        try:
            if attempt > 1:
                logger.info("Retry %d/%d for %s", attempt - 1, max_retries, url)
                time.sleep(delay)

            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response

        except requests.exceptions.Timeout:
            logger.warning("Timeout on %s (attempt %d)", url, attempt)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            logger.warning("HTTP %d on %s (attempt %d)", status, url, attempt)
            if status not in [429, 500, 502, 503, 504]:
                # Non-retryable status — fail immediately.
                return None
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error on %s (attempt %d)", url, attempt)
        except requests.exceptions.RequestException as e:
            logger.warning("Request failed for %s: %s (attempt %d)", url, e, attempt)

    logger.error("All retries exhausted for %s", url)
    return None
