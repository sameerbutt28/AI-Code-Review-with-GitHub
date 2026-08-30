"""
=============================================================================
API ROUTES
FILE: app/api/routes.py

PURPOSE: Defines all HTTP endpoints the frontend calls.
This file is kept THIN — it only receives requests and calls the workflow.

ENDPOINTS:
  POST /api/review              → Start a new code review
  GET  /api/review/{id}         → Check review status / get results
  GET  /api/review/{id}/report  → Download PDF or Markdown report
  GET  /api/health              → Health check
=============================================================================
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.models.schemas import ReviewRequest, ReviewStatusResponse
from app.services.review_workflow import run_full_review
from app.services.step4_report_generator import save_report
from app.storage import review_store

router = APIRouter()


@router.post("/review", response_model=ReviewStatusResponse)
async def start_review(request: ReviewRequest, background_tasks: BackgroundTasks):
    """User submits a GitHub URL → we start the 4-step pipeline in background."""
    repo = (request.repo_url or "").strip()
    if not repo:
        raise HTTPException(status_code=400, detail="Repository URL is required.")
    if "github.com" not in repo.lower():
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid GitHub repository URL (https://github.com/owner/repo).",
        )

    review_id = str(uuid.uuid4())
    review_store.set_status(review_id, "queued", "Review queued...")

    background_tasks.add_task(
        run_full_review,
        review_id,
        repo,
        (request.branch or "main").strip() or "main",
        request.github_token,
    )

    return ReviewStatusResponse(
        review_id=review_id,
        status="queued",
        message="Code review started. Poll /api/review/{review_id} for status.",
    )


@router.get("/review/{review_id}", response_model=ReviewStatusResponse)
async def get_review_status(review_id: str):
    """Frontend polls this endpoint until status is 'completed'."""
    status_info = review_store.get_status(review_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewStatusResponse(
        review_id=review_id,
        status=status_info["status"],
        message=status_info["message"],
        result=review_store.get_result(review_id),
        chunks_done=status_info.get("chunks_done", 0),
        chunks_total=status_info.get("chunks_total", 0),
    )


@router.get("/review/{review_id}/report")
async def download_report(review_id: str, format: str = "pdf"):
    """Download the generated PDF or Markdown report."""
    result = review_store.get_result(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found or not yet completed")

    base = f"{result.repo_name}_{review_id[:8]}"
    if format == "md":
        path = review_store.REPORTS_DIR / f"{base}.md"
        media_type, filename = "text/markdown", f"{result.repo_name}_security_report.md"
    else:
        path = review_store.REPORTS_DIR / f"{base}.pdf"
        media_type, filename = "application/pdf", f"{result.repo_name}_security_report.pdf"

    if not path.exists():
        save_report(result, review_store.REPORTS_DIR)

    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/health")
async def health_check():
    """Simple health check for demos and smoke tests."""
    return {
        "status": "healthy",
        "app": "AI Code Review",
        "version": "2.0.0",
        "environment": settings.app_env,
        "openai_configured": bool(settings.openai_api_key),
        "model": settings.openai_model,
    }
