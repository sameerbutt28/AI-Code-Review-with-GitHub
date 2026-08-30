"""
=============================================================================
ORIGINALITY HELPER
FILE: app/services/originality_helper.py

Builds unique, structured executive summaries (with bullet points) and
report fingerprints for AI Code Review FYP reports.
=============================================================================
"""

import hashlib
from collections import Counter
from datetime import datetime, timezone

from app.models.schemas import CodeReviewResult, SecurityFinding, Severity


def risk_posture(score: int) -> str:
    if score >= 75:
        return "Critical risk"
    if score >= 50:
        return "High risk"
    if score >= 25:
        return "Moderate risk"
    if score > 0:
        return "Low risk"
    return "Minimal risk"


def build_priority_actions(findings: list[SecurityFinding], limit: int = 5) -> list[str]:
    """Top remediation steps from highest-severity findings."""
    severity_order = list(Severity)
    ranked = sorted(findings, key=lambda f: severity_order.index(f.severity))
    actions: list[str] = []
    for f in ranked[:limit]:
        loc = f.file_path or "unknown file"
        if f.line_number:
            loc = f"{loc}:{f.line_number}"
        actions.append(f"[{f.severity.value.upper()}] {f.title} — review `{loc}`")
    return actions


def build_data_driven_summary(result: CodeReviewResult) -> str:
    """
    Structured executive summary with bullet points.
    Uses real scan data so each repo produces unique text.
    """
    s = result.summary
    commit = result.commit_sha[:8] if result.commit_sha else "unknown"
    posture = risk_posture(s.risk_score)

    lines: list[str] = [
        "Overview",
        f"AI Code Review analyzed `{result.repo_name}` on branch `{result.branch}` "
        f"(commit {commit}). {result.files_scanned} source file(s) were scanned "
        f"using pattern matching and chunked AI review.",
        "",
        "Key metrics",
        f"- Risk score: {s.risk_score}/100 ({posture})",
        f"- Total findings: {s.total_findings}",
        f"- Repository: {result.repo_url}",
        f"- Branch / commit: {result.branch} / {commit}",
        "",
        "Severity breakdown",
        f"- Critical: {s.critical_count}",
        f"- High: {s.high_count}",
        f"- Medium: {s.medium_count}",
        f"- Low: {s.low_count}",
        f"- Info: {s.info_count}",
    ]

    if result.findings:
        categories = Counter(f.category.value.replace("_", " ") for f in result.findings)
        lines.extend(["", "Top issue categories"])
        for name, count in categories.most_common(5):
            lines.append(f"- {name.title()}: {count}")

        actions = build_priority_actions(result.findings)
        if actions:
            lines.extend(["", "Priority actions"])
            for action in actions:
                lines.append(f"- {action}")
    else:
        lines.extend([
            "",
            "Outcome",
            "- No significant security patterns were detected in the scanned files.",
            "- Continue monitoring with each new commit.",
        ])

    return "\n".join(lines)


def merge_executive_summary(ai_summary: str, result: CodeReviewResult) -> str:
    """Combine data-driven summary with optional AI notes (bullet formatted)."""
    data_summary = build_data_driven_summary(result)
    if not ai_summary or len(ai_summary.strip()) < 30:
        return data_summary

    note_lines = ["", "Additional analysis notes"]
    # Prefer existing bullets; otherwise wrap paragraphs as bullets
    for raw in ai_summary.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ", "• ")):
            note_lines.append(line if line.startswith("- ") else f"- {line.lstrip('*• ').strip()}")
        else:
            note_lines.append(f"- {line}")

    return data_summary + "\n" + "\n".join(note_lines)


def generate_report_fingerprint(result: CodeReviewResult) -> str:
    raw = f"{result.repo_url}|{result.commit_sha}|{result.scanned_at.isoformat()}|{result.summary.total_findings}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


def get_originality_notice(result: CodeReviewResult) -> str:
    fingerprint = generate_report_fingerprint(result)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"This report was generated exclusively by AI Code Review for repository "
        f"'{result.repo_name}' (branch: {result.branch}). "
        f"Analysis is based only on source code scanned in this session. "
        f"Report ID: {fingerprint} | Generated: {timestamp}"
    )


def _severity_counts(findings: list) -> dict[Severity, int]:
    counts = {s: 0 for s in Severity}
    for f in findings:
        sev = getattr(f, "severity", None)
        if isinstance(sev, Severity):
            counts[sev] += 1
        elif isinstance(sev, str):
            try:
                counts[Severity(sev.lower())] += 1
            except ValueError:
                counts[Severity.MEDIUM] += 1
    return counts


def _diminishing_points(count: int, first_weight: float, decay: float = 0.55) -> float:
    """
    First finding contributes full weight; each extra finding contributes less.
    Prevents medium/low volume from pushing every repo to 90–100.
    """
    if count <= 0:
        return 0.0
    total = 0.0
    for i in range(count):
        total += first_weight / (1.0 + (i * decay))
    return total


def calculate_risk_score_from_findings(findings: list) -> int:
    """
    Balanced 0–100 risk score for multi-section reviews.

    Design:
    - Anchor from the worst severity present (so 1 critical matters)
    - Add diminishing points per finding (volume does not explode the score)
    - Soft cap keeps typical repos in a readable mid range
    """
    if not findings:
        return 0

    counts = _severity_counts(findings)

    # Presence anchors (not stacked — only the worst applies)
    if counts[Severity.CRITICAL] > 0:
        anchor = 42
    elif counts[Severity.HIGH] > 0:
        anchor = 28
    elif counts[Severity.MEDIUM] > 0:
        anchor = 14
    elif counts[Severity.LOW] > 0:
        anchor = 6
    else:
        anchor = 2

    # Diminishing extras (tuned for 8-section scans)
    extras = (
        _diminishing_points(counts[Severity.CRITICAL], 12.0, decay=0.65)
        + _diminishing_points(counts[Severity.HIGH], 7.0, decay=0.55)
        + _diminishing_points(counts[Severity.MEDIUM], 3.0, decay=0.45)
        + _diminishing_points(counts[Severity.LOW], 1.2, decay=0.40)
        + _diminishing_points(counts[Severity.INFO], 0.4, decay=0.35)
    )

    # Soft compression above 70 so only severe stacks approach 100
    raw = anchor + extras
    if raw > 70:
        raw = 70 + (raw - 70) * 0.45

    return int(max(0, min(100, round(raw))))


def calculate_risk_score_from_severities(findings_count: int, severities: list[Severity]) -> int:
    """Compatibility wrapper — builds lightweight finding-like objects is unnecessary; use counts."""
    class _F:
        def __init__(self, severity: Severity):
            self.severity = severity

    return calculate_risk_score_from_findings([_F(s) for s in severities])



def sort_findings_stably(findings: list) -> list:
    severity_order = {s: i for i, s in enumerate(Severity)}
    return sorted(
        findings,
        key=lambda f: (
            severity_order.get(f.severity, 99),
            f.file_path or "",
            f.line_number or 0,
            f.category.value,
            f.title.lower(),
        ),
    )
