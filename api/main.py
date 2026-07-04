"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import crawl, jobs, search
from api.scheduler import CrawlScheduler

logger = logging.getLogger(__name__)

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, _LOG_LEVEL, logging.INFO))
logger.info("Log level set to %s", _LOG_LEVEL)

_CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "http://localhost:5173")
CORS_ORIGINS = [o.strip() for o in _CORS_ORIGINS_RAW.split(",") if o.strip()]

DATABASE_PATH = os.getenv("DATABASE_PATH", "jobs.db")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Start the scheduler on boot, shut down on exit."""
    scheduler = CrawlScheduler(db_path=DATABASE_PATH)
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(
    title="Career Intelligence Agent",
    description="Discover and rank local AI/ML internships and entry-level jobs using semantic search.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
