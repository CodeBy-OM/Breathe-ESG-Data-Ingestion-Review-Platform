import React, { useState, useEffect, useCallback } from 'react';
import { recordAPI } from '../api';

const CATEGORY_LABELS = {
  'scope1_fuel': 'Scope 1 Fuel',
  'scope2_electricity': 'Scope 2 Elec.',
  'scope3_travel': 'Scope 3 Travel',
  'scope3_procurement': 'Scope 3 Proc.',
};

const STATUS_COLORS = {
  pending: 'status-pending',
  approved: 'status-approved',
  rejected: 'status-rejected',
  flagged: 'status-flagged',
};

function QualityBar({ score }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div className="quality-bar" title={`Quality: ${pct}%`}>
      <div className="quality-fill" style={{ width: `${pct}%`, background: color }}></div>
    </div>
  );
}

function RecordModal({ record, onClose, onAction }) {
  const [notes, setNotes] = useState('');
  const [acting, setActing] = useState(false);

  const act = async (action) => {
    setActing(true);
    try { await onAction(record.id, action, notes); onClose(); }
    catch (e) { alert('Action failed'); }
    finally { setActing(false); }
  };

  if (!record) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{CATEGORY_LABELS[record.category] || record.category}</h3>
            <p>{record.subcategory} · {record.activity_date}</p>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div className="detail-grid">
            <div className="detail-section">
              <h4>Normalized Values</h4>
              <div className="detail-row"><label>Quantity</label><span>{record.quantity?.toFixed(2)} {record.unit}</span></div>
              <div className="detail-row"><label>CO₂e</label><strong className="co2e">{record.co2e_kg?.toFixed(2)} kg</strong></div>
              <div className="detail-row"><label>Location</label><span>{record.location || '—'}</span></div>
              <div className="detail-row"><label>Supplier</label><span>{record.supplier || '—'}</span></div>
              {record.cost_gbp && <div className="detail-row"><label>Cost</label><span>£{record.cost_gbp?.toFixed(2)}</span></div>}
            </div>

            <div className="detail-section">
              <h4>Data Quality</h4>
              <div className="detail-row"><label>Score</label><span>{Math.round((record.quality_score || 0) * 100)}%</span></div>
              {record.quality_issues?.length > 0 && (
                <div className="issues-list">
                  {record.quality_issues.map((issue, i) => (
                    <div key={i} className="issue-item">⚠ {issue}</div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {record.normalization_notes && (
            <div className="notes-box">
              <label>Normalization notes</label>
              <p>{record.normalization_notes}</p>
            </div>
          )}

          {record.raw_data && Object.keys(record.raw_data).length > 0 && (
            <details className="raw-data-toggle">
              <summary>View raw source data</summary>
              <div className="raw-data-grid">
                {Object.entries(record.raw_data).filter(([, v]) => v != null).map(([k, v]) => (
                  <div key={k} className="raw-row">
                    <label>{k}</label>
                    <span>{String(v)}</span>
                  </div>
                ))}
              </div>
            </details>
          )}

          {!record.is_locked && (
            <div className="action-section">
              <textarea
                className="notes-input"
                placeholder="Add review notes (optional)..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={2}
              />
              <div className="action-buttons">
                <button className="btn btn-approve" onClick={() => act('approve')} disabled={acting}>
                  ✓ Approve
                </button>
                <button className="btn btn-reject" onClick={() => act('reject')} disabled={acting}>
                  ✕ Reject
                </button>
                <button className="btn btn-flag" onClick={() => act('flag')} disabled={acting}>
                  ⚑ Flag for Review
                </button>
              </div>
            </div>
          )}

          {record.is_locked && (
            <div className="locked-notice">🔒 Record locked for audit — cannot be modified</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReviewPage({ onRefresh }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState('pending');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [suspiciousOnly, setSuspiciousOnly] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const PAGE_SIZE = 50;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page };
      if (filter) params.review_status = filter;
      if (categoryFilter) params.category = categoryFilter;
      if (suspiciousOnly) params.is_suspicious = true;
      const res = await recordAPI.getRecords(params);
      setRecords(res.data.results || res.data);
      setTotalCount(res.data.count || (res.data.results || res.data).length);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filter, categoryFilter, suspiciousOnly, page]);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (id, action, notes) => {
    if (action === 'approve') await recordAPI.approve(id, notes);
    else if (action === 'reject') await recordAPI.reject(id, notes);
    else if (action === 'flag') await recordAPI.flag(id, notes);
    load(); onRefresh();
  };

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return;
    await recordAPI.bulkApprove([...selectedIds]);
    setSelectedIds(new Set());
    load(); onRefresh();
  };

  const toggleSelect = (id) => {
    const s = new Set(selectedIds);
    if (s.has(id)) s.delete(id); else s.add(id);
    setSelectedIds(s);
  };

  const toggleAll = () => {
    if (selectedIds.size === records.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(records.map(r => r.id)));
  };

  const FILTER_TABS = [
    { value: '', label: 'All' },
    { value: 'pending', label: 'Pending' },
    { value: 'flagged', label: 'Flagged ⚑' },
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
  ];

  return (
    <div className="page review-page">
      <div className="page-header">
        <div>
          <h1>Review & Approve</h1>
          <p className="page-sub">{totalCount} records · Analyst workflow</p>
        </div>
        <div className="header-actions">
          {selectedIds.size > 0 && (
            <button className="btn btn-approve" onClick={handleBulkApprove}>
              ✓ Approve {selectedIds.size} selected
            </button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={load}>↺</button>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <div className="filter-tabs">
          {FILTER_TABS.map(t => (
            <button
              key={t.value}
              className={`filter-tab ${filter === t.value ? 'active' : ''}`}
              onClick={() => { setFilter(t.value); setPage(1); }}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="filter-controls">
          <select
            className="filter-select"
            value={categoryFilter}
            onChange={e => { setCategoryFilter(e.target.value); setPage(1); }}
          >
            <option value="">All categories</option>
            <option value="scope1_fuel">Scope 1 — Fuel</option>
            <option value="scope2_electricity">Scope 2 — Electricity</option>
            <option value="scope3_travel">Scope 3 — Travel</option>
            <option value="scope3_procurement">Scope 3 — Procurement</option>
          </select>

          <label className="toggle-label">
            <input
              type="checkbox"
              checked={suspiciousOnly}
              onChange={e => { setSuspiciousOnly(e.target.checked); setPage(1); }}
            />
            <span>Suspicious only</span>
          </label>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <span>Loading records...</span>
        </div>
      ) : records.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">✓</div>
          <h3>No records to review</h3>
          <p>All records have been processed</p>
        </div>
      ) : (
        <div className="table-card">
          <table className="data-table review-table">
            <thead>
              <tr>
                <th><input type="checkbox" checked={selectedIds.size === records.length && records.length > 0} onChange={toggleAll} /></th>
                <th>Date</th>
                <th>Category</th>
                <th>Subcategory</th>
                <th>Quantity</th>
                <th>CO₂e (kg)</th>
                <th>Location</th>
                <th>Quality</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {records.map(rec => (
                <tr
                  key={rec.id}
                  className={`${rec.is_suspicious ? 'suspicious-row' : ''} ${rec.is_locked ? 'locked-row' : ''}`}
                >
                  <td onClick={e => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(rec.id)}
                      onChange={() => toggleSelect(rec.id)}
                      disabled={rec.is_locked || rec.review_status === 'approved'}
                    />
                  </td>
                  <td className="date-cell">{rec.activity_date}</td>
                  <td><span className={`cat-badge cat-${rec.category}`}>{CATEGORY_LABELS[rec.category] || rec.category}</span></td>
                  <td className="sub-cell">{rec.subcategory}</td>
                  <td className="num-cell">{rec.quantity?.toFixed(1)} <span className="unit">{rec.unit}</span></td>
                  <td className="num-cell co2-cell">{rec.co2e_kg?.toFixed(1)}</td>
                  <td className="loc-cell">{rec.location || '—'}</td>
                  <td>
                    <QualityBar score={rec.quality_score || 0} />
                  </td>
                  <td>
                    <div className="status-cell">
                      <span className={`status-badge ${STATUS_COLORS[rec.review_status]}`}>
                        {rec.review_status}
                      </span>
                      {rec.is_suspicious && <span className="flag-icon" title="Suspicious data">⚠</span>}
                      {rec.is_locked && <span className="lock-icon" title="Locked">🔒</span>}
                    </div>
                  </td>
                  <td>
                    <button className="btn btn-ghost btn-xs" onClick={() => setSelected(rec)}>
                      View →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalCount > PAGE_SIZE && (
            <div className="pagination">
              <button className="btn btn-ghost btn-sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>← Prev</button>
              <span>Page {page} of {Math.ceil(totalCount / PAGE_SIZE)}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(totalCount / PAGE_SIZE)}>Next →</button>
            </div>
          )}
        </div>
      )}

      {selected && (
        <RecordModal
          record={selected}
          onClose={() => setSelected(null)}
          onAction={handleAction}
        />
      )}
    </div>
  );
}
