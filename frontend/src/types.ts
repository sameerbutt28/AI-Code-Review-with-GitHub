export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

/** Fixed review sections — must match backend FindingCategory */
export type FindingCategory =
  | 'correctness_logic'
  | 'security'
  | 'readability_maintainability'
  | 'design_architecture'
  | 'performance_resources'
  | 'reliability_concurrency'
  | 'testing'
  | 'standards_hygiene';

export const REVIEW_SECTIONS: { id: FindingCategory; title: string; blurb: string }[] = [
  {
    id: 'correctness_logic',
    title: 'Correctness and Logic',
    blurb: 'Edge cases, error handling, control flow, return values',
  },
  {
    id: 'security',
    title: 'Security',
    blurb: 'Validation, injection, auth, secrets, crypto, exposure, dependencies',
  },
  {
    id: 'readability_maintainability',
    title: 'Readability and Maintainability',
    blurb: 'Naming, size, complexity, dead code, comments',
  },
  {
    id: 'design_architecture',
    title: 'Design and Architecture',
    blurb: 'Patterns, DRY, separation of concerns, coupling',
  },
  {
    id: 'performance_resources',
    title: 'Performance and Resources',
    blurb: 'Inefficiencies, resource cleanup, memory, caching',
  },
  {
    id: 'reliability_concurrency',
    title: 'Reliability and Concurrency',
    blurb: 'Thread safety, idempotency, timeouts, degradation',
  },
  {
    id: 'testing',
    title: 'Testing',
    blurb: 'Coverage, edge cases, meaningful assertions',
  },
  {
    id: 'standards_hygiene',
    title: 'Standards and Hygiene',
    blurb: 'Style, docs, API compatibility, configuration',
  },
];

export interface SecurityFinding {
  id: string;
  category: FindingCategory;
  severity: Severity;
  title: string;
  description: string;
  file_path?: string;
  line_number?: number;
  code_snippet?: string;
  recommendation: string;
}

export interface ReviewSummary {
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  risk_score: number;
  executive_summary: string;
}

export interface CodeReviewResult {
  review_id: string;
  repo_url: string;
  repo_name: string;
  branch: string;
  commit_sha?: string;
  scanned_at: string;
  files_scanned: number;
  summary: ReviewSummary;
  findings: SecurityFinding[];
}

export interface ReviewStatusResponse {
  review_id: string;
  status: string;
  message: string;
  result?: CodeReviewResult;
  chunks_done?: number;
  chunks_total?: number;
}

export interface ReviewRequest {
  repo_url: string;
  branch?: string;
  github_token?: string;
}
