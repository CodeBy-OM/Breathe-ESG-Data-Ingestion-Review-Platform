import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const CATEGORY_LABELS = {
  'scope1_fuel': 'Scope 1 — Fuel',
  'scope2_electricity': 'Scope 2 — Electricity',
  'scope3_travel': 'Scope 3 — Travel',
  'scope3_procurement': 'Scope 3 — Procurement',
};
const CATEGORY_COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6'];

function StatCard({ value, label, sub, accent, onClick }) {
  return (
    <div className={`stat-card ${accent || ''} ${onClick ? 'clickable' : ''}`} onClick={onClick}>
      <div className="stat-value">{value ?? '—'}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export default function Dashboard({ stats, onNavigate, onRefresh }) {
  const r = stats?.records || {};
  const e = stats?.emissions || {};

  const emissionsData = Object.entries(e.by_category || {})
    .filter(([, v]) => v > 0)
    .map(([k, v], i) => ({
      name: CATEGORY_LABELS[k] || k,
      value: v,
      color: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
    }));

  const recentImports = stats?.recent_imports || [];

  const sourceLabel = { sap: 'SAP', utility: 'Utility', travel: 'Travel' };

  return (
    <div className="page dashboard-page">
      <div className="page-header">
        <div>
          <h1>ESG Dashboard</h1>
          <p className="page-sub">FY2024 · Breathe ESG Demo · GB</p>
        </div>
        <button className="btn btn-ghost" onClick={onRefresh}>↺ Refresh</button>
      </div>

      {/* Key Metrics */}
      <div className="stat-grid">
        <StatCard
          value={r.total || 0}
          label="Total Records"
          sub={`${r.locked || 0} locked for audit`}
        />
        <StatCard
          value={`${e.total_tco2e ?? '—'}`}
          label="Total tCO₂e"
          sub="All scopes combined"
          accent="green"
        />
        <StatCard
          value={r.pending || 0}
          label="Pending Review"
          sub="Click to review"
          accent="amber"
          onClick={() => onNavigate('review')}
        />
        <StatCard
          value={r.flagged || 0}
          label="Flagged / Suspicious"
          sub="Need attention"
          accent="red"
          onClick={() => onNavigate('review')}
        />
        <StatCard
          value={r.approved || 0}
          label="Approved"
          sub={`${r.locked || 0} audit-locked`}
          accent="blue"
        />
      </div>

      {/* Charts */}
      <div className="chart-grid">
        {emissionsData.length > 0 && (
          <div className="chart-card">
            <h3>Emissions by Scope (tCO₂e)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={emissionsData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false}
                  tickFormatter={v => v.split('—')[1]?.trim() || v} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: '#1a1f2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e5e7eb' }}
                  formatter={(v) => [`${v} tCO₂e`, 'Emissions']}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {emissionsData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {emissionsData.length > 0 && (
          <div className="chart-card">
            <h3>Scope Breakdown</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={emissionsData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                  dataKey="value" paddingAngle={3}>
                  {emissionsData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1a1f2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#e5e7eb' }}
                  formatter={(v) => [`${v} tCO₂e`, '']}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="legend">
              {emissionsData.map((d, i) => (
                <div key={i} className="legend-item">
                  <span className="legend-dot" style={{ background: d.color }}></span>
                  <span>{d.name.split('—')[1]?.trim() || d.name}</span>
                  <strong>{d.value} t</strong>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Status bar */}
      {r.total > 0 && (
        <div className="status-bar-card">
          <h3>Review Progress</h3>
          <div className="progress-bar-container">
            <div className="progress-bar-track">
              <div className="progress-bar-fill approved" style={{ width: `${((r.approved || 0) / r.total) * 100}%` }}></div>
              <div className="progress-bar-fill pending" style={{ width: `${((r.pending || 0) / r.total) * 100}%` }}></div>
              <div className="progress-bar-fill flagged" style={{ width: `${((r.flagged || 0) / r.total) * 100}%` }}></div>
              <div className="progress-bar-fill rejected" style={{ width: `${((r.rejected || 0) / r.total) * 100}%` }}></div>
            </div>
            <div className="progress-labels">
              <span className="pl-approved">✓ {r.approved || 0} approved</span>
              <span className="pl-pending">⏳ {r.pending || 0} pending</span>
              <span className="pl-flagged">⚑ {r.flagged || 0} flagged</span>
              <span className="pl-rejected">✕ {r.rejected || 0} rejected</span>
            </div>
          </div>
        </div>
      )}

      {/* Recent Imports */}
      {recentImports.length > 0 && (
        <div className="table-card">
          <div className="table-header">
            <h3>Recent Imports</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('import')}>View all →</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>File</th>
                <th>Status</th>
                <th>Records</th>
                <th>Suspicious</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {recentImports.map(imp => (
                <tr key={imp.id}>
                  <td><span className={`source-badge source-${imp.source}`}>{sourceLabel[imp.source] || imp.source}</span></td>
                  <td className="filename-cell">{imp.filename}</td>
                  <td><span className={`status-badge status-${imp.status}`}>{imp.status}</span></td>
                  <td>{imp.total_rows}</td>
                  <td>
                    {imp.suspicious_rows > 0 ? (
                      <span className="suspicious-count">⚠ {imp.suspicious_rows}</span>
                    ) : '—'}
                  </td>
                  <td className="date-cell">{imp.uploaded_at ? new Date(imp.uploaded_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {r.total === 0 && (
        <div className="empty-state">
          <div className="empty-icon">◈</div>
          <h3>No data yet</h3>
          <p>Import your first data source to get started</p>
          <button className="btn btn-primary" onClick={() => onNavigate('import')}>Import Data →</button>
        </div>
      )}
    </div>
  );
}
