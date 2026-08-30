"""
=============================================================================
STEP 3: AI ANALYZER (Chunked LangChain + OpenAI)
FILE: app/services/step3_ai_analyzer.py

CHUNKED FLOW:
1. Collect source files + run pattern scan on the whole repo
2. Split files into CHUNKS (chunk_builder.py)
3. Send EACH chunk to the LLM one by one
4. Update progress: "Analyzing chunk 2/5 ..."
5. After ALL chunks finish → merge findings → build final result
6. Only then does the frontend get the completed result

CONSISTENCY:
- temperature=0 and seed from commit (+ chunk index)
- Risk score from merged findings (deterministic weights)
- Stable sorted findings
=============================================================================
"""

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.prompts import CHUNK_REVIEW_USER_PROMPT, SECURITY_REVIEW_SYSTEM_PROMPT
from app.models.schemas import (
    CodeReviewResult,
    FindingCategory,
    ReviewSummary,
    SecurityFinding,
    Severity,
)
from app.services.chunk_builder import CodeChunk, build_code_chunks, patterns_for_chunk
from app.services.originality_helper import (
    calculate_risk_score_from_findings,
    merge_executive_summary,
    sort_findings_stably,
)
from app.services.step1_github_clone import collect_source_files
from app.services.step2_pattern_scanner import run_pattern_scan

ProgressCallback = Callable[[str, str, int, int], None]


class AIFinding(BaseModel):
    category: str
    severity: str
    title: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    recommendation: str


class AIChunkResponse(BaseModel):
    """Structured response for ONE chunk only."""

    chunk_summary: str
    risk_score: int = Field(ge=0, le=100)
    findings: list[AIFinding]


# Map legacy / free-text labels from the model onto the fixed review sections.
_CATEGORY_ALIASES: dict[str, FindingCategory] = {
    "correctness_logic": FindingCategory.CORRECTNESS_LOGIC,
    "correctness": FindingCategory.CORRECTNESS_LOGIC,
    "logic": FindingCategory.CORRECTNESS_LOGIC,
    "security": FindingCategory.SECURITY,
    "hardcoded_secret": FindingCategory.SECURITY,
    "env_exposure": FindingCategory.SECURITY,
    "injection": FindingCategory.SECURITY,
    "auth": FindingCategory.SECURITY,
    "crypto": FindingCategory.SECURITY,
    "dependency": FindingCategory.SECURITY,
    "config": FindingCategory.SECURITY,
    "readability_maintainability": FindingCategory.READABILITY_MAINTAINABILITY,
    "readability": FindingCategory.READABILITY_MAINTAINABILITY,
    "maintainability": FindingCategory.READABILITY_MAINTAINABILITY,
    "design_architecture": FindingCategory.DESIGN_ARCHITECTURE,
    "design": FindingCategory.DESIGN_ARCHITECTURE,
    "architecture": FindingCategory.DESIGN_ARCHITECTURE,
    "performance_resources": FindingCategory.PERFORMANCE_RESOURCES,
    "performance": FindingCategory.PERFORMANCE_RESOURCES,
    "resources": FindingCategory.PERFORMANCE_RESOURCES,
    "reliability_concurrency": FindingCategory.RELIABILITY_CONCURRENCY,
    "reliability": FindingCategory.RELIABILITY_CONCURRENCY,
    "concurrency": FindingCategory.RELIABILITY_CONCURRENCY,
    "testing": FindingCategory.TESTING,
    "standards_hygiene": FindingCategory.STANDARDS_HYGIENE,
    "standards": FindingCategory.STANDARDS_HYGIENE,
    "hygiene": FindingCategory.STANDARDS_HYGIENE,
    "other": FindingCategory.STANDARDS_HYGIENE,
}


def _to_category(value: str) -> FindingCategory:
    key = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    try:
        return FindingCategory(key)
    except ValueError:
        return FindingCategory.STANDARDS_HYGIENE


def _to_severity(value: str) -> Severity:
    try:
        return Severity(value.lower())
    except ValueError:
        return Severity.MEDIUM


def _pattern_to_finding(raw: dict) -> SecurityFinding:
    return SecurityFinding(
        id=raw["id"],
        category=_to_category(raw["category"]),
        severity=_to_severity(raw["severity"]),
        title=raw["title"],
        description=raw["description"],
        file_path=raw.get("file_path"),
        line_number=raw.get("line_number"),
        code_snippet=raw.get("code_snippet"),
        recommendation=raw["recommendation"],
    )


def _ai_to_finding(raw: AIFinding, index: int, chunk_index: int) -> SecurityFinding:
    return SecurityFinding(
        id=f"ai-c{chunk_index}-{index + 1}",
        category=_to_category(raw.category),
        severity=_to_severity(raw.severity),
        title=raw.title,
        description=raw.description,
        file_path=raw.file_path,
        line_number=raw.line_number,
        code_snippet=raw.code_snippet,
        recommendation=raw.recommendation,
    )


def _remove_duplicate_findings(findings: list[SecurityFinding]) -> list[SecurityFinding]:
    """
    Keep one finding per location+section+title.
    Prefer higher severity when duplicates collide.
    """
    best: dict[tuple, SecurityFinding] = {}
    severity_order = list(Severity)

    for f in findings:
        title_key = (f.title or "").strip().lower()
        key = (
            (f.file_path or "").replace("\\", "/").lower(),
            f.line_number or 0,
            f.category.value,
            title_key,
        )
        existing = best.get(key)
        if existing is None or severity_order.index(f.severity) < severity_order.index(existing.severity):
            best[key] = f

    return sort_findings_stably(list(best.values()))


def _stable_finding_id(finding: SecurityFinding) -> str:
    """Deterministic ID so the same issue looks identical across re-scans."""
    raw = "|".join([
        finding.category.value,
        finding.severity.value,
        (finding.file_path or "").replace("\\", "/").lower(),
        str(finding.line_number or 0),
        (finding.title or "").strip().lower(),
    ])
    return "f-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _stabilize_findings(findings: list[SecurityFinding]) -> list[SecurityFinding]:
    stabilized: list[SecurityFinding] = []
    for f in sort_findings_stably(findings):
        stabilized.append(f.model_copy(update={"id": _stable_finding_id(f)}))
    return stabilized


def _count_by_severity(findings: list[SecurityFinding]) -> dict[Severity, int]:
    counts = {s: 0 for s in Severity}
    for f in findings:
        counts[f.severity] += 1
    return counts


def _seed_for_chunk(commit_sha: str, chunk_index: int) -> int:
    raw = f"{commit_sha}:{chunk_index}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2**31)


def _merge_chunk_summaries(repo_name: str, chunk_summaries: list[str], total_chunks: int) -> str:
    """Build AI appendix notes as bullet points after all chunks finish."""
    if not chunk_summaries:
        return ""
    lines = [
        f"Repository `{repo_name}` was processed in {total_chunks} independent code chunk(s); findings were then merged.",
    ]
    for i, summary in enumerate(chunk_summaries, start=1):
        clean = summary.strip()
        if clean:
            lines.append(f"Chunk {i}/{total_chunks}: {clean}")
    return "\n".join(lines)


def _build_result(
    repo_name: str,
    branch: str,
    repo_url: str,
    commit_sha: str,
    files_scanned: int,
    all_findings: list[SecurityFinding],
    ai_summary: str,
) -> CodeReviewResult:
    all_findings = _stabilize_findings(all_findings)
    counts = _count_by_severity(all_findings)
    risk_score = calculate_risk_score_from_findings(all_findings)

    result = CodeReviewResult(
        review_id=str(uuid.uuid4()),
        repo_url=repo_url,
        repo_name=repo_name,
        branch=branch,
        commit_sha=commit_sha,
        scanned_at=datetime.now(timezone.utc),
        files_scanned=files_scanned,
        summary=ReviewSummary(
            total_findings=len(all_findings),
            critical_count=counts[Severity.CRITICAL],
            high_count=counts[Severity.HIGH],
            medium_count=counts[Severity.MEDIUM],
            low_count=counts[Severity.LOW],
            info_count=counts[Severity.INFO],
            risk_score=risk_score,
            executive_summary="",
        ),
        findings=all_findings,
    )

    result.summary.executive_summary = merge_executive_summary(ai_summary, result)
    return result


async def _analyze_one_chunk(
    chunk: CodeChunk,
    repo_name: str,
    branch: str,
    commit_sha: str,
    chunk_patterns: list[dict],
) -> AIChunkResponse:
    """Send a single chunk to the LLM and return structured findings."""
    system_prompt = SECURITY_REVIEW_SYSTEM_PROMPT.format(
        chunk_index=chunk.chunk_index,
        total_chunks=chunk.total_chunks,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", CHUNK_REVIEW_USER_PROMPT),
    ])

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        seed=_seed_for_chunk(commit_sha, chunk.chunk_index),
    )
    chain = prompt | llm.with_structured_output(AIChunkResponse)

    return await chain.ainvoke({
        "repo_name": repo_name,
        "branch": branch,
        "chunk_index": chunk.chunk_index,
        "total_chunks": chunk.total_chunks,
        "file_count": chunk.file_count,
        "file_list": ", ".join(chunk.file_paths),
        "code_bundle": chunk.code_text,
        "pattern_findings": json.dumps(chunk_patterns, indent=2, sort_keys=True),
    })


async def analyze_repository(
    repo_name: str,
    branch: str,
    repo_path: Path,
    repo_url: str,
    commit_sha: str,
    on_progress: ProgressCallback | None = None,
) -> CodeReviewResult:
    """
    Run pattern scan + chunked AI analysis.

    Results are returned ONLY after every chunk is processed and merged.
    """
    def report(status: str, message: str, done: int = 0, total: int = 0) -> None:
        if on_progress:
            on_progress(status, message, done, total)

    files = collect_source_files(repo_path)
    report("analyzing", f"Pattern scanning {len(files)} source file(s)...", 0, 0)
    pattern_raw = run_pattern_scan(files, repo_path)

    chunks = build_code_chunks(files, repo_path)
    total_chunks = len(chunks)

    ai_findings: list[SecurityFinding] = []
    chunk_summaries: list[str] = []

    if not settings.openai_api_key:
        report("analyzing", "No OpenAI key — using pattern scan only.", total_chunks, total_chunks)
        ai_summary = (
            f"Pattern-based scan of {repo_name} found {len(pattern_raw)} potential issue(s). "
            f"Set OPENAI_API_KEY in .env to enable chunked AI analysis."
        )
    elif total_chunks == 0:
        report("analyzing", "No source files found to send to the AI.", 0, 0)
        ai_summary = f"No analyzable source files were found in `{repo_name}`."
    else:
        report(
            "analyzing",
            f"Split into {total_chunks} chunk(s). Starting LLM analysis...",
            0,
            total_chunks,
        )

        finding_counter = 0
        for chunk in chunks:
            report(
                "analyzing",
                f"Analyzing {chunk.label} ({chunk.file_count} file(s))...",
                chunk.chunk_index - 1,
                total_chunks,
            )

            chunk_patterns = patterns_for_chunk(pattern_raw, chunk)
            try:
                chunk_response = await _analyze_one_chunk(
                    chunk=chunk,
                    repo_name=repo_name,
                    branch=branch,
                    commit_sha=commit_sha,
                    chunk_patterns=chunk_patterns,
                )
                chunk_summaries.append(chunk_response.chunk_summary)
                for f in chunk_response.findings:
                    ai_findings.append(_ai_to_finding(f, finding_counter, chunk.chunk_index))
                    finding_counter += 1
            except Exception as exc:
                # Continue other chunks so one failure doesn't kill the whole review
                chunk_summaries.append(
                    f"Chunk {chunk.chunk_index} analysis failed ({type(exc).__name__}); "
                    f"pattern hints for this chunk were still included."
                )

            report(
                "analyzing",
                f"Finished {chunk.label}. Merging results after all chunks...",
                chunk.chunk_index,
                total_chunks,
            )

        report(
            "analyzing",
            f"All {total_chunks} chunk(s) processed. Merging findings...",
            total_chunks,
            total_chunks,
        )
        ai_summary = _merge_chunk_summaries(repo_name, chunk_summaries, total_chunks)

    pattern_findings = [_pattern_to_finding(p) for p in pattern_raw]
    all_findings = _remove_duplicate_findings(pattern_findings + ai_findings)

    return _build_result(
        repo_name=repo_name,
        branch=branch,
        repo_url=repo_url,
        commit_sha=commit_sha,
        files_scanned=len(files),
        all_findings=all_findings,
        ai_summary=ai_summary,
    )
