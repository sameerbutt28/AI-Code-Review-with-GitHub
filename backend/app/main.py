"""
=============================================================================
MAIN APPLICATION ENTRY POINT
FILE: app/main.py

PURPOSE: Creates the FastAPI application and registers routes.
Run with: python run.py
=============================================================================
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.storage import review_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create required folders when the server starts."""
    Path(settings.temp_clone_dir).mkdir(parents=True, exist_ok=True)
    review_store.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    review_store.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="AI Code Review API",
    description=(
        "AI Code Review — automated multi-section GitHub code review "
        "(clone → pattern scan → chunked AI analysis → PDF/Markdown reports)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "AI Code Review",
        "version": "2.0.0",
        "environment": settings.app_env,
        "docs": "/docs",
        "health": "/api/health",
        "openai_configured": bool(settings.openai_api_key),
    }
