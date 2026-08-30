"""
=============================================================================
STEP 2: PATTERN SCANNER
FILE: app/services/step2_pattern_scanner.py

Fast regex screening for common SECURITY issues (no AI).
All pattern findings are tagged with category = "security"
so they appear under the Security section card.
=============================================================================
"""

import re
from pathlib import Path

from app.services.step1_github_clone import get_relative_path, read_file_content

# (regex_pattern, issue_key) — all mapped to section "security"
SECURITY_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "hardcoded_secret"),
    (r"(?i)(aws_access_key_id|aws_secret_access_key)\s*[=:]", "hardcoded_secret"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "hardcoded_secret"),
    (r"sk-[a-zA-Z0-9]{20,}", "hardcoded_secret"),
    (r"ghp_[a-zA-Z0-9]{36,}", "hardcoded_secret"),
    (r"eval\s*\(", "injection"),
    (r"exec\s*\(", "injection"),
    (r"innerHTML\s*=", "injection"),
    (r"dangerouslySetInnerHTML", "injection"),
    (r"verify\s*=\s*False", "weak_crypto"),
    (r"md5\s*\(", "weak_crypto"),
    (r"console\.log\s*\(", "debug_leftover"),
    (r"print\s*\(.*password|print\s*\(.*token|print\s*\(.*secret", "sensitive_log"),
]


def _make_finding_id(counter: int) -> str:
    return f"pattern-{counter}"


def _write_original_description(rel_path: str, line_num: int, issue_key: str) -> str:
    label = issue_key.replace("_", " ")
    return (
        f"During automated scanning of `{rel_path}` at line {line_num}, "
        f"AI Code Review detected a pattern associated with {label}. "
        f"This finding is specific to the scanned commit of this repository."
    )


def _write_original_recommendation(rel_path: str, line_num: int, issue_key: str) -> str:
    if issue_key == "hardcoded_secret":
        return (
            f"Remove the exposed value in `{rel_path}` (line {line_num}) and "
            f"store it in environment variables or a secrets manager instead."
        )
    if issue_key == "injection":
        return (
            f"Review the dynamic code execution in `{rel_path}` (line {line_num}) "
            f"and replace it with a safer alternative that validates all inputs."
        )
    if issue_key == "weak_crypto":
        return (
            f"Replace the weak cryptographic usage in `{rel_path}` (line {line_num}) "
            f"with a modern algorithm such as SHA-256 or bcrypt."
        )
    if issue_key == "debug_leftover":
        return (
            f"Remove leftover debug logging in `{rel_path}` (line {line_num}) "
            f"or gate it behind a proper logger with levels."
        )
    if issue_key == "sensitive_log":
        return (
            f"Avoid printing secrets in `{rel_path}` (line {line_num}); "
            f"redact sensitive fields before logging."
        )
    return f"Investigate and fix the issue found in `{rel_path}` at line {line_num}."


def _section_and_severity(issue_key: str) -> tuple[str, str]:
    """Map pattern issue → review section + severity."""
    if issue_key == "debug_leftover":
        return "readability_maintainability", "low"
    if issue_key == "hardcoded_secret":
        return "security", "high"
    if issue_key == "sensitive_log":
        return "security", "medium"
    return "security", "medium"


def run_pattern_scan(files: list[Path], repo_path: Path) -> list[dict]:
    """
    Scan all files with regex patterns.
    Returns findings deduplicated by file+line (deterministic order).
    """
    findings: list[dict] = []
    seen_lines: set[tuple[str, int]] = set()
    finding_id = 0

    for file_path in files:
        content = read_file_content(file_path)
        if not content:
            continue

        rel_path = get_relative_path(file_path, repo_path)
        lines = content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            line_key = (rel_path, line_num)
            if line_key in seen_lines:
                continue

            matched_issue = None
            for pattern, issue_key in SECURITY_PATTERNS:
                if re.search(pattern, line):
                    matched_issue = issue_key
                    break

            if not matched_issue:
                continue

            seen_lines.add(line_key)
            finding_id += 1
            section, severity = _section_and_severity(matched_issue)
            findings.append({
                "id": _make_finding_id(finding_id),
                "category": section,
                "severity": severity,
                "title": f"{matched_issue.replace('_', ' ').title()} in {rel_path}",
                "description": _write_original_description(rel_path, line_num, matched_issue),
                "file_path": rel_path,
                "line_number": line_num,
                "code_snippet": line.strip()[:200],
                "recommendation": _write_original_recommendation(rel_path, line_num, matched_issue),
            })

    return findings
