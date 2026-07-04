"""ATS platform detection via URL patterns and page HTML analysis."""

from dataclasses import dataclass


@dataclass
class ATSDetectionResult:
    """Result of detecting an ATS platform from a URL or page HTML.

    Attributes:
        ats_name: Name of the detected ATS (e.g. "greenhouse", "lever"), or None.
        confidence: Certainty level from 0.0 (no match) to 1.0 (exact match).
        reason: Machine-readable label explaining how the match was made.
    """

    ats_name: str | None
    confidence: float
    reason: str


# URL substrings mapped to ATS names (highest confidence).
_URL_PATTERNS: dict[str, str] = {
    "boards.greenhouse.io": "greenhouse",
    "greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "lever.co": "lever",
    "myworkdayjobs.com": "workday",
    "wd1.myworkdayjobs.com": "workday",
    "wd5.myworkdayjobs.com": "workday",
    "smartrecruiters.com": "smartrecruiters",
    "bamboohr.com": "bamboohr",
    "icims.com": "icims",
    "taleo.net": "taleo",
    "oraclecloud.com": "taleo",
    "ashbyhq.com": "ashby",
    "jobs.ashbyhq.com": "ashby",
    "jobvite.com": "jobvite",
}

# HTML meta-tag / keyword clues (medium-to-low confidence).
_META_CLUES: dict[str, str] = {
    "greenhouse": "greenhouse",
    "lever": "lever",
    "workday": "workday",
    "smartrecruiters": "smartrecruiters",
    "bamboohr": "bamboohr",
    "icims": "icims",
    "taleo": "taleo",
    "ashby": "ashby",
}


def detect_ats(url: str, page_html: str | None = None) -> ATSDetectionResult:
    """Detect the ATS platform from a career page URL and optional HTML.

    Uses a two-layer cascade:
    1. URL substring match (confidence 1.0)
    2. HTML content analysis (confidence 0.7)

    Args:
        url: The career page URL to analyse.
        page_html: Optional raw HTML content for deeper analysis.

    Returns:
        An ATSDetectionResult with the detected ATS name, confidence, and reason.
    """
    url_lower = url.lower()

    # Layer 1: URL pattern match (high confidence).
    for pattern, ats_name in _URL_PATTERNS.items():
        if pattern in url_lower:
            return ATSDetectionResult(
                ats_name=ats_name,
                confidence=1.0,
                reason="url_pattern_match",
            )

    # Layer 2: HTML content analysis (medium confidence).
    if page_html:
        html_lower = page_html.lower()
        for clue, ats_name in _META_CLUES.items():
            if clue in html_lower:
                return ATSDetectionResult(
                    ats_name=ats_name,
                    confidence=0.7,
                    reason="meta_tag_detection",
                )

    return ATSDetectionResult(
        ats_name=None,
        confidence=0.0,
        reason="no_match",
    )
