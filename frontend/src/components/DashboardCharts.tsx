import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
} from 'recharts';
import { BarChart3, PieChart as PieChartIcon, Gauge } from 'lucide-react';
import type { CodeReviewResult } from '../types';
import type { Theme } from '../hooks/useTheme';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#6b7280',
};

const CATEGORY_COLORS = [
  '#6366f1', '#8b5cf6', '#06b6d4', '#22c55e',
  '#f97316', '#ec4899', '#14b8a6', '#a855f7',
];

interface DashboardChartsProps {
  result: CodeReviewResult;
  theme: Theme;
}

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <span className="chart-tooltip-label">{label}</span>
      <span className="chart-tooltip-value">{payload[0].value}</span>
    </div>
  );
}

export function DashboardCharts({ result, theme }: DashboardChartsProps) {
  const { summary, findings } = result;

  const severityData = [
    { name: 'Critical', value: summary.critical_count, fill: SEVERITY_COLORS.critical },
    { name: 'High', value: summary.high_count, fill: SEVERITY_COLORS.high },
    { name: 'Medium', value: summary.medium_count, fill: SEVERITY_COLORS.medium },
    { name: 'Low', value: summary.low_count, fill: SEVERITY_COLORS.low },
    { name: 'Info', value: summary.info_count, fill: SEVERITY_COLORS.info },
  ];

  const categoryMap = new Map<string, number>();
  const labelFor = (cat: string) => {
    const found = [
      ['correctness_logic', 'Correctness'],
      ['security', 'Security'],
      ['readability_maintainability', 'Readability'],
      ['design_architecture', 'Design'],
      ['performance_resources', 'Performance'],
      ['reliability_concurrency', 'Reliability'],
      ['testing', 'Testing'],
      ['standards_hygiene', 'Standards'],
    ].find(([id]) => id === cat);
    return found?.[1] ?? cat.replace(/_/g, ' ');
  };
  for (const f of findings) {
    const cat = labelFor(f.category);
    categoryMap.set(cat, (categoryMap.get(cat) ?? 0) + 1);
  }
  const categoryData = Array.from(categoryMap.entries()).map(([name, value], i) => ({
    name,
    value,
    fill: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
  }));

  const riskData = [{ name: 'Risk', value: summary.risk_score, fill: summary.risk_score >= 75 ? '#ef4444' : summary.risk_score >= 50 ? '#f97316' : summary.risk_score >= 25 ? '#eab308' : '#22c55e' }];

  const gridColor = theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.08)';
  const axisColor = theme === 'dark' ? '#71717a' : '#94a3b8';
  const tooltipBg = theme === 'dark' ? '#18181b' : '#ffffff';

  return (
    <div className="dashboard-charts">
      <div className="chart-card glass-card">
        <div className="chart-card-header">
          <BarChart3 size={18} />
          <div>
            <h3>Findings by Severity</h3>
            <p>Breakdown across risk levels</p>
          </div>
        </div>
        <div className="chart-body">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={severityData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
              <XAxis dataKey="name" tick={{ fill: axisColor, fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: axisColor, fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: theme === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(15,23,42,0.04)' }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={48}>
                {severityData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="chart-card glass-card">
        <div className="chart-card-header">
          <PieChartIcon size={18} />
          <div>
            <h3>Findings by Category</h3>
            <p>Issue type distribution</p>
          </div>
        </div>
        <div className="chart-body chart-body-pie">
          {categoryData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {categoryData.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: tooltipBg, border: `1px solid ${gridColor}`, borderRadius: 8, fontSize: 13 }}
                    formatter={(value, name) => [`${value ?? 0}`, String(name)]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="chart-legend">
                {categoryData.map((item) => (
                  <div key={item.name} className="legend-item">
                    <span className="legend-dot" style={{ background: item.fill }} />
                    <span className="legend-label">{item.name}</span>
                    <span className="legend-value">{item.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="chart-empty">No categorized findings</div>
          )}
        </div>
      </div>

      <div className="chart-card glass-card">
        <div className="chart-card-header">
          <Gauge size={18} />
          <div>
            <h3>Risk Score</h3>
            <p>Overall security posture</p>
          </div>
        </div>
        <div className="chart-body chart-body-gauge">
          <ResponsiveContainer width="100%" height={200}>
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="70%"
              outerRadius="100%"
              barSize={14}
              data={riskData}
              startAngle={180}
              endAngle={0}
            >
              <RadialBar
                background={{ fill: gridColor }}
                dataKey="value"
                cornerRadius={8}
                fill={riskData[0].fill}
              />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="gauge-center">
            <span className="gauge-value" style={{ color: riskData[0].fill }}>{summary.risk_score}</span>
            <span className="gauge-label">out of 100</span>
          </div>
          <div className="gauge-scale">
            <span>Low</span>
            <span>High</span>
          </div>
        </div>
      </div>
    </div>
  );
}
