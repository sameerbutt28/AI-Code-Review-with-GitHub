"""
=============================================================================
STEP 1: GITHUB CLONE
FILE: app/services/step1_github_clone.py

WHAT THIS FILE DOES:
1. Takes a GitHub URL from the user
2. Clones the repository to a temporary folder on disk
3. Collects source code files to scan (skips node_modules, .git, etc.)
4. Reads file contents for analysis

USED BY: review_workflow.py (Step 1 of the pipeline)
=============================================================================
"""

import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from git import Repo

from app.core.config import settings

# Folders we skip when walking the repo
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "coverage"}

# File types we consider as source code
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rb", ".php",
    ".cs", ".rs", ".yaml", ".yml", ".json", ".env", ".toml", ".sql", ".html", ".css",
}


@dataclass
class ClonedRepo:
    """Holds information about a cloned repository."""
    repo_id: str
    repo_url: str
    repo_name: str
    branch: str
    local_path: Path
    commit_sha: str


def parse_github_url(repo_url: str) -> tuple[str, str]:
    """Convert user URL to clone URL and extract repo name."""
    parsed = urlparse(repo_url.rstrip("/"))
    path = parsed.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not path or "/" not in path:
        raise ValueError("Invalid GitHub repository URL")
    clone_url = f"https://github.com/{path}.git"
    repo_name = path.split("/")[-1]
    return clone_url, repo_name


def clone_repository(repo_url: str, branch: str = "main", github_token: str | None = None) -> ClonedRepo:
    """
    Clone a GitHub repo to temp_clone_dir.
    Returns ClonedRepo with local path and commit SHA.
    """
    clone_url, repo_name = parse_github_url(repo_url)
    repo_id = str(uuid.uuid4())
    local_path = Path(settings.temp_clone_dir) / repo_id

    if local_path.exists():
        shutil.rmtree(local_path)
    local_path.mkdir(parents=True, exist_ok=True)

    if github_token:
        clone_url = clone_url.replace("https://", f"https://{github_token}@")

    git_repo = Repo.clone_from(clone_url, local_path, branch=branch, depth=1)

    return ClonedRepo(
        repo_id=repo_id,
        repo_url=repo_url,
        repo_name=repo_name,
        branch=branch,
        local_path=local_path,
        commit_sha=git_repo.head.commit.hexsha,
    )


def cleanup_repo(local_path: Path) -> None:
    """Delete cloned repo folder after analysis is done."""
    if local_path.exists():
        shutil.rmtree(local_path, ignore_errors=True)


def collect_source_files(repo_path: Path) -> list[Path]:
    """Walk repo and return list of source files (max limit from settings)."""
    files: list[Path] = []
    max_bytes = settings.max_file_size_kb * 1024

    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in filenames:
            file_path = Path(root) / filename
            ext = file_path.suffix.lower()
            if ext not in CODE_EXTENSIONS and filename.lower() not in {"dockerfile", "makefile", ".env"}:
                continue
            if file_path.stat().st_size > max_bytes:
                continue
            files.append(file_path)

    files.sort(key=lambda p: str(p))
    return files[: settings.max_files_to_scan]


def read_file_content(file_path: Path) -> str:
    """Read a single file as UTF-8 text."""
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def get_relative_path(file_path: Path, repo_path: Path) -> str:
    """Get file path relative to repo root (e.g. src/main.py)."""
    return str(file_path.relative_to(repo_path)).replace("\\", "/")


def build_code_bundle(files: list[Path], repo_path: Path, max_chars: int = 80000) -> str:
    """
    Combine source files into one text block for the AI.
    Each line is numbered so the AI can reference line numbers.
    """
    parts: list[str] = []
    total = 0

    for file_path in files:
        rel = get_relative_path(file_path, repo_path)
        content = read_file_content(file_path)
        if not content.strip():
            continue

        numbered = "\n".join(f"{i:4d}| {line}" for i, line in enumerate(content.splitlines(), start=1))
        block = f"\n--- FILE: {rel} ---\n{numbered}\n"

        if total + len(block) > max_chars:
            parts.append(f"\n--- FILE: {rel} ---\n[truncated]\n")
            break
        parts.append(block)
        total += len(block)

    return "".join(parts)
