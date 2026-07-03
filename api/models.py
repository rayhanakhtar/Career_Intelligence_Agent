"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel


class JobResponse(BaseModel):
    """Schema for a single job record returned by the API."""

    id: int
    title: str
    company: str
    location: str
    description: str
    apply_url: str
    department: str
    employment_type: str
    posted_at: str
    source: str
    source_id: str
    created_at: str


class JobWithScore(JobResponse):
    """A job record enriched with a semantic match score."""

    match_score: float


class SearchRequest(BaseModel):
    """Request body for the /search endpoint."""

    resume_text: str
    top_k: int = 10
    locations: list[str] | None = None


class SearchResponse(BaseModel):
    """Response containing ranked job results."""

    results: list[JobWithScore]


class CrawlRequest(BaseModel):
    """Request body for the /crawl endpoint."""

    source: str
    token: str


class CrawlResponse(BaseModel):
    """Immediate response returned by the /crawl endpoint."""

    task_id: str
    status: str


class CrawlAllRequest(BaseModel):
    """Request body for the /crawl/all endpoint (currently empty — reserved for future filters)."""

    pass


class CrawlAllResponse(BaseModel):
    """Response returned by the /crawl/all endpoint."""

    task_id: str
    status: str


class CrawlAllResultResponse(BaseModel):
    """Summary of per-company crawl results."""

    task_id: str
    status: str
    results: dict[str, int]


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
