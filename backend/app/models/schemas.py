"""
=============================================================================
DATA MODELS (Pydantic Schemas)
FILE: app/models/schemas.py

PURPOSE: Defines the shape of all data in the system.
Teachers can explain: "We use Pydantic to validate API requests and responses."

Main models:
- ReviewRequest     → what the user sends (repo URL, branch)
- CodeReviewResult  → full review output
- SecurityFinding   → one issue found under a review section
- ReviewSummary     → counts and risk score
=============================================================================
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Primary review sections used for scanning and dashboard cards."""

    CORRECTNESS_LOGIC = "correctness_logic"
    SECURITY = "security"
    READABILITY_MAINTAINABILITY = "readability_maintainability"
    DESIGN_ARCHITECTURE = "design_architecture"
    PERFORMANCE_RESOURCES = "performance_resources"
    RELIABILITY_CONCURRENCY = "reliability_concurrency"
    TESTING = "testing"
    STANDARDS_HYGIENE = "standards_hygiene"


# Display labels (order used on dashboard cards)
REVIEW_SECTIONS: list[tuple[FindingCategory, str]] = [
    (FindingCategory.CORRECTNESS_LOGIC, "Correctness and Logic"),
    (FindingCategory.SECURITY, "Security"),
    (FindingCategory.READABILITY_MAINTAINABILITY, "Readability and Maintainability"),
    (FindingCategory.DESIGN_ARCHITECTURE, "Design and Architecture"),
    (FindingCategory.PERFORMANCE_RESOURCES, "Performance and Resources"),
    (FindingCategory.RELIABILITY_CONCURRENCY, "Reliability and Concurrency"),
    (FindingCategory.TESTING, "Testing"),
    (FindingCategory.STANDARDS_HYGIENE, "Standards and Hygiene"),
]


class SecurityFinding(BaseModel):
    id: str
    category: FindingCategory
    severity: Severity
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: str


class ReviewSummary(BaseModel):
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    risk_score: int = Field(ge=0, le=100, description="Overall risk score 0-100")
    executive_summary: str


class CodeReviewResult(BaseModel):
    review_id: str
    repo_url: str
    repo_name: str
    branch: str
    commit_sha: Optional[str] = None
    scanned_at: datetime
    files_scanned: int
    summary: ReviewSummary
    findings: list[SecurityFinding]


class ReviewRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL (HTTPS)")
    branch: str = "main"
    github_token: Optional[str] = Field(
        default=None,
        description="Optional GitHub PAT for private repositories",
    )


class WebhookPayload(BaseModel):
    ref: Optional[str] = None
    repository: Optional[dict] = None
    after: Optional[str] = None


class ReviewStatusResponse(BaseModel):
    review_id: str
    status: str
    message: str
    result: Optional[CodeReviewResult] = None
    chunks_done: int = 0
    chunks_total: int = 0
