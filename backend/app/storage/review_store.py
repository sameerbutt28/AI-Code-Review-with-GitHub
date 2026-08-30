"""
=============================================================================
FILE: app/storage/review_store.py
PURPOSE: Storage for review jobs, results, and commit-level analysis cache.

CONSISTENCY:
Same repo URL + branch + commit SHA → same findings and risk score.
Cache lives in memory AND on disk so results survive backend restarts.
=============================================================================
"""

import json
import re
from pathlib import Path

from app.models.schemas import CodeReviewResult

REPORTS_DIR = Path("./reports")
CACHE_DIR = Path("./cache/analysis")

# { review_id: { "status", "message", "chunks_done", "chunks_total" } }
review_status: dict[str, dict] = {}

review_results: dict[str, CodeReviewResult] = {}

# Key: "normalized_repo|branch|commit_sha"
analysis_cache: dict[str, CodeReviewResult] = {}


def normalize_repo_url(repo_url: str) -> str:
    """Normalize URLs so slight paste differences still hit the same cache key."""
    url = (repo_url or "").strip().rstrip("/")
    url = re.sub(r"\.git$", "", url, flags=re.IGNORECASE)
    url = re.sub(r"^https?://(www\.)?", "https://", url, flags=re.IGNORECASE)
    return url.lower()


def make_cache_key(repo_url: str, branch: str, commit_sha: str) -> str:
    return f"{normalize_repo_url(repo_url)}|{(branch or 'main').strip()}|{commit_sha}"


def _cache_file_path(repo_url: str, branch: str, commit_sha: str) -> Path:
    key = make_cache_key(repo_url, branch, commit_sha)
    # Safe filename from hash of the key
    import hashlib

    digest = hashlib.sha256(key.encode()).hexdigest()[:40]
    return CACHE_DIR / f"{digest}.json"


def get_cached_analysis(repo_url: str, branch: str, commit_sha: str) -> CodeReviewResult | None:
    """Return cached analysis for this exact commit (memory first, then disk)."""
    key = make_cache_key(repo_url, branch, commit_sha)

    if key in analysis_cache:
        return analysis_cache[key]

    path = _cache_file_path(repo_url, branch, commit_sha)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = CodeReviewResult.model_validate(data)
        analysis_cache[key] = result
        return result
    except Exception:
        # Corrupt/outdated cache file — ignore and re-analyze
        return None


def cache_analysis(repo_url: str, branch: str, commit_sha: str, result: CodeReviewResult) -> None:
    """Store analysis in memory and on disk for identical future scans."""
    key = make_cache_key(repo_url, branch, commit_sha)
    analysis_cache[key] = result

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_file_path(repo_url, branch, commit_sha)
    # Persist findings + scores; strip volatile fields that shouldn't affect scoring
    payload = result.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def set_status(
    review_id: str,
    status: str,
    message: str,
    chunks_done: int = 0,
    chunks_total: int = 0,
) -> None:
    """Update job progress. Results stay empty until the job completes."""
    review_status[review_id] = {
        "status": status,
        "message": message,
        "chunks_done": chunks_done,
        "chunks_total": chunks_total,
    }


def get_status(review_id: str) -> dict | None:
    return review_status.get(review_id)


def save_result(review_id: str, result: CodeReviewResult) -> None:
    review_results[review_id] = result


def get_result(review_id: str) -> CodeReviewResult | None:
    return review_results.get(review_id)
