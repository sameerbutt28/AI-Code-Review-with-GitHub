import { Bug, CheckCircle2, FileCode } from 'lucide-react';
import type { CodeReviewResult, FindingCategory, SecurityFinding } from '../types';
import { REVIEW_SECTIONS } from '../types';

function FindingItem({ finding }: { finding: SecurityFinding }) {
  return (
    <div className={`section-finding sev-${finding.severity}`}>
      <div className="section-finding-header">
        <span className="section-finding-title">{finding.title}</span>
        <span className={`severity-badge ${finding.severity}`}>{finding.severity}</span>
      </div>
      <div className="finding-meta">
        {finding.file_path && (
          <span>
            <FileCode size={12} /> {finding.file_path}
            {finding.line_number ? `:${finding.line_number}` : ''}
          </span>
        )}
      </div>
      <p className="finding-description">{finding.description}</p>
      {finding.code_snippet && <pre className="code-snippet">{finding.code_snippet}</pre>}
      <div className="finding-recommendation">
        <strong>Recommendation:</strong> {finding.recommendation}
      </div>
    </div>
  );
}

function SectionCard({
  title,
  blurb,
  findings,
}: {
  title: string;
  blurb: string;
  findings: SecurityFinding[];
}) {
  const count = findings.length;

  return (
    <div className={`section-card glass-card ${count === 0 ? 'section-clean' : 'section-has-issues'}`}>
      <div className="section-card-header">
        <div className="section-card-title-wrap">
          <h3>{title}</h3>
          <p>{blurb}</p>
        </div>
        <span className={`section-count-badge ${count === 0 ? 'clean' : 'issues'}`}>
          {count === 0 ? (
            <>
              <CheckCircle2 size={14} /> Clear
            </>
          ) : (
            <>
              <Bug size={14} /> {count} issue{count === 1 ? '' : 's'}
            </>
          )}
        </span>
      </div>

      {count === 0 ? (
        <p className="section-empty">No issues detected in this section for the scanned files.</p>
      ) : (
        <div className="section-findings">
          {findings.map((f) => (
            <FindingItem key={f.id} finding={f} />
          ))}
        </div>
      )}
    </div>
  );
}

function groupBySection(findings: SecurityFinding[]): Record<FindingCategory, SecurityFinding[]> {
  const groups = Object.fromEntries(
    REVIEW_SECTIONS.map((s) => [s.id, [] as SecurityFinding[]]),
  ) as Record<FindingCategory, SecurityFinding[]>;

  for (const finding of findings) {
    const key = (REVIEW_SECTIONS.some((s) => s.id === finding.category)
      ? finding.category
      : 'standards_hygiene') as FindingCategory;
    groups[key].push(finding);
  }

  return groups;
}

export function SectionReviewCards({ result }: { result: CodeReviewResult }) {
  const groups = groupBySection(result.findings);

  const orderedSections = [...REVIEW_SECTIONS].sort((a, b) => {
    const aCount = groups[a.id].length;
    const bCount = groups[b.id].length;
    // Sections with findings first; clear sections last. Keep relative order within each group.
    if (aCount > 0 && bCount === 0) return -1;
    if (aCount === 0 && bCount > 0) return 1;
    return 0;
  });

  return (
    <div className="section-review">
      <div className="results-header">
        <h2>Review Sections ({result.findings.length} total findings)</h2>
      </div>
      <div className="section-cards">
        {orderedSections.map((section) => (
          <SectionCard
            key={section.id}
            title={section.title}
            blurb={section.blurb}
            findings={groups[section.id]}
          />
        ))}
      </div>
    </div>
  );
}
