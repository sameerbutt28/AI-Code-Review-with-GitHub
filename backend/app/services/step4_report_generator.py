"""
=============================================================================
STEP 4: REPORT GENERATOR (Advanced)
FILE: app/services/step4_report_generator.py

Creates structured PDF + Markdown security reports with:
- cover / header metadata
- dashboard charts
- bullet-formatted executive summary
- risk posture & priority actions
- category breakdown
- findings grouped by severity
=============================================================================
"""

from collections import Counter
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.schemas import CodeReviewResult, SecurityFinding, Severity
from app.services.chart_renderer import build_dashboard_flowables
from app.services.originality_helper import (
    build_priority_actions,
    generate_report_fingerprint,
    get_originality_notice,
    risk_posture,
)


SEVERITY_COLORS = {
    Severity.CRITICAL: colors.HexColor("#dc2626"),
    Severity.HIGH: colors.HexColor("#ea580c"),
    Severity.MEDIUM: colors.HexColor("#ca8a04"),
    Severity.LOW: colors.HexColor("#2563eb"),
    Severity.INFO: colors.HexColor("#6b7280"),
}


def _escape_pdf(text: str | None) -> str:
    if not text:
        return ""
    cleaned = str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
    return escape(cleaned, entities={'"': "&quot;", "'": "&apos;"})


def _parse_summary_blocks(summary: str) -> list[tuple[str, list[str]]]:
    """
    Parse structured summary text into (heading|para, items) blocks.
    Headings are bare lines without leading '- '.
    Bullets start with '- ', '* ', or '• '.
    """
    blocks: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_items: list[str] = []
    current_paras: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_items, current_paras
        if current_heading or current_items or current_paras:
            content = current_paras + current_items
            blocks.append((current_heading, content))
        current_heading = ""
        current_items = []
        current_paras = []

    for raw in summary.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ", "• ")):
            current_items.append(line[2:].strip())
        elif not current_items and not current_paras and (
            line in {
                "Overview", "Key metrics", "Severity breakdown",
                "Top issue categories", "Priority actions", "Outcome",
                "Additional analysis notes",
            }
            or (len(line) < 48 and not line.endswith("."))
        ):
            flush()
            current_heading = line
        else:
            if current_items:
                # paragraph after bullets starts a soft new section without known heading
                pass
            current_paras.append(line)

    flush()
    return blocks


def _add_page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(0.75 * inch, 0.45 * inch, "AI Code Review Security Report")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def generate_markdown_report(result: CodeReviewResult) -> str:
    """Advanced Markdown report with structured sections."""
    fingerprint = generate_report_fingerprint(result)
    s = result.summary
    posture = risk_posture(s.risk_score)
    commit = result.commit_sha or "N/A"

    lines = [
        "# AI Code Review Advanced Security Report",
        "",
        f"> **Report ID:** `{fingerprint}`  ",
        f"> **Generated for:** `{result.repo_name}`  ",
        f"> **Risk posture:** **{posture}** ({s.risk_score}/100)",
        "",
        "## 1. Repository Profile",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Repository | {result.repo_name} |",
        f"| URL | {result.repo_url} |",
        f"| Branch | `{result.branch}` |",
        f"| Commit | `{commit}` |",
        f"| Scanned at | {result.scanned_at.isoformat()} |",
        f"| Files scanned | {result.files_scanned} |",
        f"| Total findings | {s.total_findings} |",
        "",
        "## 2. Executive Summary",
        "",
    ]

    for heading, items in _parse_summary_blocks(s.executive_summary):
        if heading:
            lines.extend([f"### {heading}", ""])
        # Detect if items look like bullets or paragraphs
        bullet_like = len(items) > 1 or (items and len(items[0]) < 220)
        for item in items:
            if heading and bullet_like and not item.endswith("."):
                lines.append(f"- {item}")
            elif heading in {
                "Key metrics", "Severity breakdown", "Top issue categories",
                "Priority actions", "Outcome", "Additional analysis notes",
            } or item.startswith(("[", "Critical", "High", "Medium", "Low", "Info", "Risk", "Total", "Repository", "Branch", "Chunk")):
                lines.append(f"- {item}")
            else:
                lines.append(item)
                lines.append("")
        lines.append("")

    lines.extend([
        "## 3. Risk Posture",
        "",
        f"- **Score:** {s.risk_score}/100",
        f"- **Classification:** {posture}",
        f"- **Critical / High / Medium / Low / Info:** "
        f"{s.critical_count} / {s.high_count} / {s.medium_count} / {s.low_count} / {s.info_count}",
        "",
        "## 4. Severity Overview",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| Critical | {s.critical_count} |",
        f"| High | {s.high_count} |",
        f"| Medium | {s.medium_count} |",
        f"| Low | {s.low_count} |",
        f"| Info | {s.info_count} |",
        f"| **Total** | **{s.total_findings}** |",
        "",
    ])

    if result.findings:
        categories = Counter(f.category.value.replace("_", " ").title() for f in result.findings)
        lines.extend(["## 5. Category Breakdown", "", "| Category | Count |", "|----------|-------|"])
        for name, count in categories.most_common():
            lines.append(f"| {name} | {count} |")
        lines.append("")

        actions = build_priority_actions(result.findings, limit=7)
        lines.extend(["## 6. Priority Remediation Plan", ""])
        for i, action in enumerate(actions, start=1):
            lines.append(f"{i}. {action}")
        lines.append("")

    lines.extend([
        "## 7. Analysis Methodology",
        "",
        "- **Step 1:** Clone the selected GitHub branch (shallow clone).",
        "- **Step 2:** Regex pattern scan for secrets, injection, and weak crypto.",
        "- **Step 3:** Split source files into chunks and analyze each chunk with an LLM.",
        "- **Step 4:** Merge findings, compute a deterministic risk score, and generate this report.",
        "",
        "## 8. Detailed Findings",
        "",
    ])

    if not result.findings:
        lines.append("_No security findings detected._")
    else:
        by_sev: dict[Severity, list[SecurityFinding]] = {sev: [] for sev in Severity}
        for f in result.findings:
            by_sev[f.severity].append(f)

        finding_no = 0
        for sev in Severity:
            group = by_sev[sev]
            if not group:
                continue
            lines.extend([f"### {sev.value.upper()} ({len(group)})", ""])
            for f in group:
                finding_no += 1
                lines.extend([
                    f"#### {finding_no}. {f.title}",
                    "",
                    f"- **Category:** `{f.category.value}`",
                    f"- **Location:** `{f.file_path or 'N/A'}`"
                    + (f" (line {f.line_number})" if f.line_number else ""),
                    f"- **Description:** {f.description}",
                ])
                if f.code_snippet:
                    lines.extend(["", "```", f.code_snippet, "```", ""])
                lines.extend([
                    f"- **Recommendation:** {f.recommendation}",
                    "",
                    "---",
                    "",
                ])

    lines.extend(["", "## 9. Report Integrity", "", f"*{get_originality_notice(result)}*", ""])
    return "\n".join(lines)


def generate_pdf_report(result: CodeReviewResult) -> bytes:
    """Advanced PDF report with structured sections and bullet summary."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CLTitle", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=20, textColor=colors.HexColor("#0f172a"), spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "CLSub", parent=styles["Normal"], alignment=TA_CENTER,
        fontSize=10, textColor=colors.HexColor("#64748b"), spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "CLH2", parent=styles["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=8,
        textColor=colors.HexColor("#1e293b"),
    )
    subheading_style = ParagraphStyle(
        "CLH3", parent=styles["Heading3"], fontSize=10, spaceBefore=8, spaceAfter=4,
        textColor=colors.HexColor("#334155"),
    )
    body_style = ParagraphStyle(
        "CLBody", parent=styles["Normal"], fontSize=9, leading=13, spaceAfter=4, alignment=TA_LEFT,
    )
    bullet_style = ParagraphStyle(
        "CLBullet", parent=body_style, leftIndent=14, bulletIndent=0, spaceAfter=3,
    )
    footer_style = ParagraphStyle(
        "CLFooter", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#64748b"), leading=10,
    )
    snippet_style = ParagraphStyle(
        "CLSnippet", parent=styles["Code"], fontSize=7,
        backColor=colors.HexColor("#f1f5f9"), leading=10, spaceBefore=2, spaceAfter=4,
    )

    fingerprint = generate_report_fingerprint(result)
    s = result.summary
    posture = risk_posture(s.risk_score)
    story = []

    # Cover header
    header = Table(
        [[Paragraph("<b>AI Code Review</b> Advanced Security Report", title_style)]],
        colWidths=[7 * inch],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#6366f1")),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.extend([
        header,
        Spacer(1, 8),
        Paragraph(
            f"Report ID: {_escape_pdf(fingerprint)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Risk posture: <b>{_escape_pdf(posture)}</b> ({s.risk_score}/100)",
            subtitle_style,
        ),
    ])

    # Profile table
    story.append(Paragraph("1. Repository Profile", heading_style))
    profile = [
        ["Field", "Value"],
        ["Repository", result.repo_name],
        ["URL", result.repo_url],
        ["Branch", result.branch],
        ["Commit", (result.commit_sha or "N/A")[:40]],
        ["Scanned (UTC)", result.scanned_at.strftime("%Y-%m-%d %H:%M")],
        ["Files scanned", str(result.files_scanned)],
        ["Total findings", str(s.total_findings)],
    ]
    profile_table = Table(profile, colWidths=[1.6 * inch, 5.2 * inch])
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([profile_table, Spacer(1, 10)])

    # Charts
    story.append(Paragraph("2. Security Dashboard", heading_style))
    chart_width = 2.15 * inch
    charts = build_dashboard_flowables(result, chart_width)
    dashboard = Table([[charts[0], charts[1], charts[2]]], colWidths=[chart_width + 4] * 3)
    dashboard.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#18181b")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#2e2e35")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([dashboard, Spacer(1, 12)])

    # Executive summary with bullets
    story.append(Paragraph("3. Executive Summary", heading_style))
    for heading, items in _parse_summary_blocks(s.executive_summary):
        if heading:
            story.append(Paragraph(_escape_pdf(heading), subheading_style))
        for item in items:
            # Treat short/listed lines as bullets when under a section heading
            if heading or item.startswith(("[", "Critical", "High", "Medium", "Chunk", "Risk", "Total")):
                story.append(Paragraph(f"• {_escape_pdf(item)}", bullet_style))
            else:
                story.append(Paragraph(_escape_pdf(item), body_style))
    story.append(Spacer(1, 6))

    # Risk posture box
    story.append(Paragraph("4. Risk Posture", heading_style))
    risk_color = (
        "#dc2626" if s.risk_score >= 75 else
        "#ea580c" if s.risk_score >= 50 else
        "#ca8a04" if s.risk_score >= 25 else
        "#16a34a"
    )
    risk_box = Table(
        [[Paragraph(
            f"<b>Score:</b> {s.risk_score}/100 &nbsp;&nbsp; "
            f"<font color='{risk_color}'><b>{_escape_pdf(posture)}</b></font><br/>"
            f"Critical {s.critical_count} · High {s.high_count} · Medium {s.medium_count} · "
            f"Low {s.low_count} · Info {s.info_count}",
            body_style,
        )]],
        colWidths=[6.8 * inch],
    )
    risk_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb") if s.risk_score >= 25 else colors.HexColor("#ecfdf5")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(risk_color)),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([risk_box, Spacer(1, 10)])

    # Severity + category tables side logic
    story.append(Paragraph("5. Severity Overview", heading_style))
    overview = [
        ["Severity", "Count"],
        ["Critical", str(s.critical_count)],
        ["High", str(s.high_count)],
        ["Medium", str(s.medium_count)],
        ["Low", str(s.low_count)],
        ["Info", str(s.info_count)],
        ["Total", str(s.total_findings)],
    ]
    overview_table = Table(overview, colWidths=[2.2 * inch, 1.4 * inch])
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
    ]))
    story.extend([overview_table, Spacer(1, 10)])

    if result.findings:
        story.append(Paragraph("6. Category Breakdown", heading_style))
        categories = Counter(f.category.value.replace("_", " ").title() for f in result.findings)
        cat_rows = [["Category", "Count"]] + [[n, str(c)] for n, c in categories.most_common()]
        cat_table = Table(cat_rows, colWidths=[3.5 * inch, 1.2 * inch])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312e81")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7d2fe")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([cat_table, Spacer(1, 10)])

        story.append(Paragraph("7. Priority Remediation Plan", heading_style))
        for i, action in enumerate(build_priority_actions(result.findings, limit=7), start=1):
            story.append(Paragraph(f"{i}. {_escape_pdf(action)}", bullet_style))
        story.append(Spacer(1, 8))

    story.append(Paragraph("8. Analysis Methodology", heading_style))
    for step in [
        "Clone the selected GitHub branch using a shallow Git clone.",
        "Run regex pattern scanning for secrets, injection sinks, and weak cryptography.",
        "Split source files into chunks and analyze each chunk independently with an LLM.",
        "Merge findings, compute a deterministic risk score, and produce this report.",
    ]:
        story.append(Paragraph(f"• {_escape_pdf(step)}", bullet_style))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e1")))
    story.append(Paragraph("9. Detailed Findings", heading_style))

    if not result.findings:
        story.append(Paragraph("No security findings detected.", body_style))
    else:
        by_sev: dict[Severity, list[SecurityFinding]] = {sev: [] for sev in Severity}
        for f in result.findings:
            by_sev[f.severity].append(f)

        finding_no = 0
        for sev in Severity:
            group = by_sev[sev]
            if not group:
                continue
            sev_color = SEVERITY_COLORS.get(sev, colors.grey)
            story.append(Paragraph(
                f'<font color="{sev_color.hexval()}"><b>{sev.value.upper()} — {len(group)} finding(s)</b></font>',
                subheading_style,
            ))
            for f in group:
                finding_no += 1
                block = [
                    Paragraph(
                        f'<font color="{sev_color.hexval()}"><b>{finding_no}. {_escape_pdf(f.title)}</b></font>',
                        body_style,
                    ),
                    Paragraph(
                        f"<b>Category:</b> {_escape_pdf(f.category.value)} &nbsp;|&nbsp; "
                        f"<b>File:</b> {_escape_pdf(f.file_path or 'N/A')} &nbsp;|&nbsp; "
                        f"<b>Line:</b> {f.line_number or 'N/A'}",
                        body_style,
                    ),
                    Paragraph(_escape_pdf(f.description), body_style),
                ]
                if f.code_snippet:
                    block.append(Paragraph(
                        f"<b>Code:</b> <font face='Courier' size='7'>{_escape_pdf(f.code_snippet[:300])}</font>",
                        snippet_style,
                    ))
                block.append(Paragraph(
                    f"<b>Recommendation:</b> {_escape_pdf(f.recommendation)}",
                    body_style,
                ))
                block.append(Spacer(1, 6))
                story.append(KeepTogether(block))

    story.extend([
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e1")),
        Spacer(1, 6),
        Paragraph("10. Report Integrity", heading_style),
        Paragraph(_escape_pdf(get_originality_notice(result)), footer_style),
    ])

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return buffer.getvalue()


def save_report(result: CodeReviewResult, reports_dir: Path) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    base = f"{result.repo_name}_{result.review_id[:8]}"
    md_path = reports_dir / f"{base}.md"
    pdf_path = reports_dir / f"{base}.pdf"
    md_path.write_text(generate_markdown_report(result), encoding="utf-8")
    pdf_path.write_bytes(generate_pdf_report(result))
    return md_path, pdf_path
