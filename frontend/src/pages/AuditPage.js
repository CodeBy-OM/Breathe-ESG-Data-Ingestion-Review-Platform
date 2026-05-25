import React, { useState, useEffect } from 'react';
import { recordAPI, dashboardAPI } from '../api';

export default function AuditPage({ onRefresh }) {
  const [stats, setStats] = useState(null);
  const [locking, setLocking] = useState(false);
  const [locked, setLocked] = useState(null);

  useEffect(() => {
    dashboardAPI.getStats().then(r => setStats(r.data)).catch(() => {});
  }, []);

  const handleLock = async () => {
    if (!window.confirm('Lock all approved records for audit? This cannot be undone.')) return;
    setLocking(true);
    try {
      const res = await recordAPI.lockApproved();
      setLocked(res.data.locked);
      onRefresh();
      dashboardAPI.getStats().then(r => setStats(r.data)).catch(() => {});
    } catch (e) {
      alert('Lock failed');
    } finally {
      setLocking(false);
    }
  };

  const r = stats?.records || {};
  const e = stats?.emissions || {};
  const readyToLock = (r.approved || 0) - (r.locked || 0);

  const CATEGORY_LABELS = {
    'scope1_fuel': 'Scope 1 — Fuel Combustion',
    'scope2_electricity': 'Scope 2 — Electricity',
    'scope3_travel': 'Scope 3 — Business Travel',
    'scope3_procurement': 'Scope 3 — Procurement',
  };

  return (
    <div className="page audit-page">
      <div className="page-header">
        <div>
          <h1>Audit Lock</h1>
          <p className="page-sub">Finalise and lock approved records for external audit</p>
        </div>
      </div>

      {/* Audit readiness */}
      <div className="audit-status-card">
        <div className="audit-status-header">
          <div className="audit-icon">{r.locked > 0 ? '🔒' : '⊞'}</div>
          <div>
            <h3>Audit Readiness</h3>
            <p>{r.locked || 0} records currently locked · {readyToLock} approved and ready to lock</p>
          </div>
          <div className={`readiness-badge ${readyToLock > 0 ? 'ready' : 'complete'}`}>
            {readyToLock > 0 ? `${readyToLock} ready` : 'Up to date'}
          </div>
        </div>

        <div className="audit-stat-row">
          <div className="audit-stat">
            <span className="audit-stat-val">{r.total || 0}</span>
            <label>Total Records</label>
          </div>
          <div className="audit-stat">
            <span className="audit-stat-val green">{r.approved || 0}</span>
            <label>Approved</label>
          </div>
          <div className="audit-stat">
            <span className="audit-stat-val blue">{r.locked || 0}</span>
            <label>Locked</label>
          </div>
          <div className="audit-stat">
            <span className="audit-stat-val amber">{r.pending || 0}</span>
            <label>Still Pending</label>
          </div>
          <div className="audit-stat">
            <span className="audit-stat-val red">{r.flagged || 0}</span>
            <label>Flagged</label>
          </div>
        </div>

        {r.pending > 0 && (
          <div className="alert alert-amber">
            ⚠ {r.pending} records are still pending review. Consider reviewing before locking.
          </div>
        )}

        {r.flagged > 0 && (
          <div className="alert alert-red">
            ⚑ {r.flagged} flagged records have not been resolved. These will not be locked.
          </div>
        )}

        {readyToLock > 0 && (
          <button className="btn btn-primary btn-large" onClick={handleLock} disabled={locking}>
            {locking ? '⏳ Locking...' : `🔒 Lock ${readyToLock} approved records for audit`}
          </button>
        )}

        {locked !== null && (
          <div className="alert alert-green">
            ✓ {locked} records successfully locked for audit.
          </div>
        )}
      </div>

      {/* Emissions summary for audit report */}
      <div className="table-card">
        <h3>Emissions Summary — Audit Report Preview</h3>
        <p className="table-sub">FY2024 · Breathe ESG Demo · Reporting period Jan–Dec 2024</p>

        <table className="data-table audit-table">
          <thead>
            <tr>
              <th>GHG Category</th>
              <th>Scope</th>
              <th>tCO₂e</th>
              <th>% of Total</th>
              <th>Records</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(e.by_category || {}).map(([cat, co2]) => {
              const scope = cat.startsWith('scope1') ? '1' : cat.startsWith('scope2') ? '2' : '3';
              const pct = e.total_tco2e > 0 ? ((co2 / e.total_tco2e) * 100).toFixed(1) : '0.0';
              return (
                <tr key={cat}>
                  <td>{CATEGORY_LABELS[cat] || cat}</td>
                  <td><span className={`scope-badge scope-${scope}`}>Scope {scope}</span></td>
                  <td className="num-cell"><strong>{co2.toFixed(2)}</strong></td>
                  <td>
                    <div className="pct-bar">
                      <div className="pct-fill" style={{ width: `${pct}%` }}></div>
                      <span>{pct}%</span>
                    </div>
                  </td>
                  <td>—</td>
                </tr>
              );
            })}
            <tr className="total-row">
              <td><strong>Total GHG Emissions</strong></td>
              <td>All scopes</td>
              <td className="num-cell"><strong>{e.total_tco2e?.toFixed(2) || '0.00'} tCO₂e</strong></td>
              <td>100%</td>
              <td><strong>{r.locked || 0} locked</strong></td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Audit trail info */}
      <div className="info-card">
        <h4>What locking does</h4>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-icon">🔒</span>
            <div>
              <strong>Immutable records</strong>
              <p>Locked records cannot be edited, approved, or rejected — protecting audit integrity</p>
            </div>
          </div>
          <div className="info-item">
            <span className="info-icon">📋</span>
            <div>
              <strong>Full audit trail</strong>
              <p>Every approval, rejection, and edit is tracked with timestamp and user</p>
            </div>
          </div>
          <div className="info-item">
            <span className="info-icon">🏢</span>
            <div>
              <strong>Multi-tenant isolation</strong>
              <p>Each company's data is fully isolated — no cross-tenant data leakage</p>
            </div>
          </div>
          <div className="info-item">
            <span className="info-icon">📊</span>
            <div>
              <strong>GHG Protocol aligned</strong>
              <p>Scope 1, 2, 3 categorisation follows GHG Protocol Corporate Standard</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
