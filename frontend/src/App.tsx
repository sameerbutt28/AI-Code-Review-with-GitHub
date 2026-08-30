import { useEffect, useState } from 'react';
import {
  Shield,
  Search,
  Download,
  FileText,
  AlertTriangle,
  Sun,
  Moon,
  Github,
  GitBranch,
  KeyRound,
  Lock,
  Bug,
  Table2,
} from 'lucide-react';
import { startReview, pollReview, getReportUrl } from './api';
import { useTheme } from './hooks/useTheme';
import { DashboardCharts } from './components/DashboardCharts';
import { SummaryTable } from './components/SummaryTable';
import { SectionReviewCards } from './components/SectionReviewCards';
import { APP_NAME, APP_TAGLINE } from './constants';
import type { CodeReviewResult, ReviewStatusResponse } from './types';
import './App.css';

const PROGRESS_STEPS = ['queued', 'cloning', 'analyzing', 'generating_report', 'completed'];

function getStepIndex(status: string): number {
  const idx = PROGRESS_STEPS.indexOf(status);
  return idx === -1 ? 0 : idx;
}

function ReviewForm({ onSubmit, loading }: { onSubmit: (url: string, branch: string, token: string) => void; loading: boolean }) {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [token, setToken] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (repoUrl.trim()) onSubmit(repoUrl.trim(), branch.trim() || 'main', token.trim());
  };

  return (
    <form className="review-form glass-card" onSubmit={handleSubmit}>
      <div className="form-header">
        <div className="form-header-icon">
          <Github size={20} />
        </div>
        <div>
          <h2>Start a Review</h2>
          <p>Enter your repository details below</p>
        </div>
      </div>

      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="repo-url">
            <Github size={14} /> Repository URL
          </label>
          <input
            id="repo-url"
            type="url"
            placeholder="https://github.com/owner/repository"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="branch">
              <GitBranch size={14} /> Branch
            </label>
            <input
              id="branch"
              type="text"
              placeholder="main"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="token">
              <KeyRound size={14} /> GitHub Token
            </label>
            <input
              id="token"
              type="password"
              placeholder="ghp_... (optional)"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              disabled={loading}
            />
            <p className="form-hint">Required for private repositories</p>
          </div>
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading || !repoUrl.trim()}>
          <Search size={18} />
          {loading ? 'Analyzing Repository...' : 'Start Security Review'}
        </button>
      </div>
    </form>
  );
}

function ProgressCard({ status }: { status: ReviewStatusResponse }) {
  const currentStep = getStepIndex(status.status);
  const chunksDone = status.chunks_done ?? 0;
  const chunksTotal = status.chunks_total ?? 0;
  const showChunks = chunksTotal > 0 && status.status === 'analyzing';
  const chunkPercent = showChunks ? Math.round((chunksDone / chunksTotal) * 100) : 0;

  return (
    <div className="progress-card glass-card">
      <div className="progress-steps">
        {PROGRESS_STEPS.slice(0, -1).map((step, i) => (
          <div
            key={step}
            className={`progress-step ${i < currentStep ? 'done' : ''} ${i === currentStep ? 'active' : ''}`}
          />
        ))}
      </div>
      <div className="spinner" />
      <p className="progress-status">{status.status.replace(/_/g, ' ')}</p>
      <p className="progress-message">{status.message}</p>
      {showChunks && (
        <div className="chunk-progress">
          <div className="chunk-progress-meta">
            <span>Code chunks</span>
            <span>{chunksDone} / {chunksTotal} processed</span>
          </div>
          <div className="chunk-progress-bar">
            <div className="chunk-progress-fill" style={{ width: `${chunkPercent}%` }} />
          </div>
          <p className="chunk-progress-hint">
            Results appear only after every chunk is analyzed and merged.
          </p>
        </div>
      )}
    </div>
  );
}

function StatPills({ result }: { result: CodeReviewResult }) {
  const { summary } = result;
  const pills = [
    { label: 'Critical', value: summary.critical_count, color: 'var(--critical)' },
    { label: 'High', value: summary.high_count, color: 'var(--high)' },
    { label: 'Medium', value: summary.medium_count, color: 'var(--medium)' },
    { label: 'Low', value: summary.low_count, color: 'var(--low)' },
    { label: 'Total', value: summary.total_findings, color: 'var(--accent)' },
    { label: 'Files', value: result.files_scanned, color: 'var(--text-primary)' },
  ];

  return (
    <div className="stat-pills">
      {pills.map((p) => (
        <div key={p.label} className="stat-pill glass-card">
          <span className="stat-pill-value" style={{ color: p.color }}>{p.value}</span>
          <span className="stat-pill-label">{p.label}</span>
        </div>
      ))}
    </div>
  );
}

function Results({ result, theme }: { result: CodeReviewResult; theme: 'light' | 'dark' }) {
  return (
    <div className="results">
      <div className="results-meta glass-card">
        <div className="results-meta-info">
          <h2>{result.repo_name}</h2>
          <p>
            <GitBranch size={14} /> {result.branch}
            {result.commit_sha && <span className="meta-sep">·</span>}
            {result.commit_sha && <span className="mono">{result.commit_sha.slice(0, 7)}</span>}
          </p>
        </div>
        <div className="download-actions">
          <a href={getReportUrl(result.review_id, 'pdf')} className="btn btn-secondary" download>
            <Download size={16} /> PDF Report
          </a>
          <a href={getReportUrl(result.review_id, 'md')} className="btn btn-secondary" download>
            <FileText size={16} /> Markdown
          </a>
        </div>
      </div>

      <StatPills result={result} />
      <DashboardCharts result={result} theme={theme} />

      <div className="executive-summary glass-card">
        <h3><Table2 size={18} /> Review Summary</h3>
        <SummaryTable result={result} />
      </div>

      <SectionReviewCards result={result} />
    </div>
  );
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<ReviewStatusResponse | null>(null);
  const [result, setResult] = useState<CodeReviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hoverBg, setHoverBg] = useState(false);

  useEffect(() => {
    const onMouseMove = (event: MouseEvent) => {
      document.documentElement.style.setProperty('--mouse-x', `${event.clientX}px`);
      document.documentElement.style.setProperty('--mouse-y', `${event.clientY}px`);

      const target = event.target as HTMLElement | null;
      // Only show floating dots over empty background — not cards/nav/buttons
      const overUi = Boolean(
        target?.closest('.glass-card, .navbar, .btn, .theme-toggle, .feature-pill, input, label, a, button'),
      );
      setHoverBg(!overUi);
    };

    const onMouseLeave = () => setHoverBg(false);

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    document.documentElement.addEventListener('mouseleave', onMouseLeave);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      document.documentElement.removeEventListener('mouseleave', onMouseLeave);
    };
  }, []);

  const handleReview = async (repoUrl: string, branch: string, token: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setProgress(null);

    try {
      const started = await startReview({
        repo_url: repoUrl,
        branch,
        github_token: token || undefined,
      });
      setProgress(started);

      const completed = await pollReview(started.review_id, setProgress);
      if (completed.result) {
        setResult(completed.result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setLoading(false);
      setProgress(null);
    }
  };

  return (
    <div className="page">
      <div className="mesh-bg" />
      <div className="grid-overlay" />
      <div className={`hover-dots${hoverBg ? ' is-active' : ''}`} aria-hidden="true" />

      <nav className="navbar">
        <div className="nav-brand">
          <div className="nav-logo">
            <Shield size={18} color="white" />
          </div>
          {APP_NAME}
        </div>
        <div className="nav-actions">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </nav>

      <div className="app">
        <header className="hero">
          <h1>{APP_NAME}</h1>
          <p>{APP_TAGLINE}</p>
          <div className="hero-features">
            <span className="feature-pill"><Lock size={13} /> Secret Detection</span>
            <span className="feature-pill"><Bug size={13} /> Vulnerability Scan</span>
            <span className="feature-pill"><FileText size={13} /> PDF Reports</span>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <AlertTriangle size={18} />
            {error}
          </div>
        )}

        <ReviewForm onSubmit={handleReview} loading={loading} />

        {loading && progress && <ProgressCard status={progress} />}

        {result && <Results result={result} theme={theme} />}
      </div>
    </div>
  );
}
