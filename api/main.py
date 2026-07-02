"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import crawl, jobs, search

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Career Intelligence Agent",
    description="Discover and rank local AI/ML internships and entry-level jobs using semantic search.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(search.router)
app.include_router(crawl.router)


@app.get("/health", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
