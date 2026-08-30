"""
=============================================================================
REVIEW WORKFLOW (Main Pipeline)
FILE: app/services/review_workflow.py

Pipeline:
  Step 1 → Clone GitHub repository
  Step 2 → Pattern scan (regex)
  Step 3 → Split into CHUNKS → LLM each chunk → MERGE (only then show results)
  Step 4 → Generate PDF/Markdown report
=============================================================================
"""

from datetime import datetime, timezone

from app.models.schemas import CodeReviewResult
from app.services.step1_github_clone import cleanup_repo, clone_repository
from app.services.step3_ai_analyzer import analyze_repository
from app.services.step4_report_generator import save_report
from app.storage import review_store


async def run_full_review(
    review_id: str,
    repo_url: str,
    branch: str,
    github_token: str | None,
) -> CodeReviewResult:
    """Execute the full pipeline. Final findings appear only after all chunks merge."""
    cloned = None

    try:
        review_store.set_status(review_id, "cloning", "Cloning repository from GitHub...")
        cloned = clone_repository(repo_url, branch, github_token)

        cached = review_store.get_cached_analysis(cloned.repo_url, cloned.branch, cloned.commit_sha)

        if cached:
            review_store.set_status(
                review_id,
                "analyzing",
                "Same unchanged commit found — returning identical cached findings and scores...",
                1,
                1,
            )
            # Keep findings + risk score identical; only bind this job's review_id
            result = cached.model_copy(update={
                "review_id": review_id,
                "scanned_at": datetime.now(timezone.utc),
            })
        else:
            def on_progress(status: str, message: str, done: int, total: int) -> None:
                review_store.set_status(review_id, status, message, done, total)

            review_store.set_status(
                review_id,
                "analyzing",
                "Preparing source files for chunked AI analysis...",
            )
            result = await analyze_repository(
                repo_name=cloned.repo_name,
                branch=cloned.branch,
                repo_path=cloned.local_path,
                repo_url=cloned.repo_url,
                commit_sha=cloned.commit_sha,
                on_progress=on_progress,
            )
            result.review_id = review_id
            review_store.cache_analysis(cloned.repo_url, cloned.branch, cloned.commit_sha, result)

        review_store.set_status(
            review_id,
            "generating_report",
            "All chunks merged. Generating PDF and Markdown reports...",
        )
        save_report(result, review_store.REPORTS_DIR)

        # Result is saved ONLY here — frontend sees findings after this
        review_store.save_result(review_id, result)
        review_store.set_status(
            review_id,
            "completed",
            "Review completed. All chunks processed and results are ready.",
        )
        return result

    except Exception as exc:
        review_store.set_status(review_id, "failed", str(exc))
        raise

    finally:
        if cloned:
            cleanup_repo(cloned.local_path)
