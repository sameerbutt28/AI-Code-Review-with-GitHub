import type { CodeReviewResult } from '../types';

function shortCommit(sha?: string): string {
  return sha ? sha.slice(0, 7) : '—';
}

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function riskLabel(score: number): string {
  if (score >= 75) return 'Critical risk';
  if (score >= 50) return 'High risk';
  if (score >= 25) return 'Moderate risk';
  return 'Low risk';
}

/** Replaces the long executive-summary text with a compact overview table. */
export function SummaryTable({ result }: { result: CodeReviewResult }) {
  const { summary } = result;

  const rows: { label: string; value: string }[] = [
    { label: 'Repository', value: result.repo_name },
    { label: 'Branch', value: result.branch },
    { label: 'Commit', value: shortCommit(result.commit_sha) },
    { label: 'Files scanned', value: String(result.files_scanned) },
    { label: 'Total findings', value: String(summary.total_findings) },
    { label: 'Risk score', value: `${summary.risk_score} / 100 · ${riskLabel(summary.risk_score)}` },
    { label: 'Critical', value: String(summary.critical_count) },
    { label: 'High', value: String(summary.high_count) },
    { label: 'Medium', value: String(summary.medium_count) },
    { label: 'Low', value: String(summary.low_count) },
    { label: 'Info', value: String(summary.info_count) },
    { label: 'Scanned at', value: formatWhen(result.scanned_at) },
  ];

  return (
    <div className="data-table-wrap">
      <table className="data-table profile-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td className="col-label">{row.label}</td>
              <td className="col-value">{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
