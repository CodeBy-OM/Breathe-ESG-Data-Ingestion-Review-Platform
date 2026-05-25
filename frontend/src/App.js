import React, { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import ImportPage from './pages/ImportPage';
import ReviewPage from './pages/ReviewPage';
import AuditPage from './pages/AuditPage';
import { dashboardAPI } from './api';
import './App.css';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '⬡' },
  { id: 'import', label: 'Import Data', icon: '↑' },
  { id: 'review', label: 'Review & Approve', icon: '✓' },
  { id: 'audit', label: 'Audit Lock', icon: '⊞' },
];

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [stats, setStats] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = () => setRefreshKey(k => k + 1);

  useEffect(() => {
    dashboardAPI.getStats().then(r => setStats(r.data)).catch(() => {});
  }, [refreshKey]);

  const pending = stats?.records?.pending || 0;
  const flagged = stats?.records?.flagged || 0;
  const reviewCount = pending + flagged;

  const renderPage = () => {
    switch (page) {
      case 'dashboard': return <Dashboard stats={stats} onNavigate={setPage} onRefresh={refresh} />;
      case 'import': return <ImportPage onImportComplete={() => { refresh(); setPage('review'); }} />;
      case 'review': return <ReviewPage key={refreshKey} onRefresh={refresh} />;
      case 'audit': return <AuditPage key={refreshKey} onRefresh={refresh} />;
      default: return <Dashboard stats={stats} onNavigate={setPage} onRefresh={refresh} />;
    }
  };

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">Breathe<strong>ESG</strong></span>
        </div>
        <div className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} onClick={() => setPage(item.id)}>
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
              {item.id === 'review' && reviewCount > 0 && <span className="nav-badge">{reviewCount}</span>}
            </button>
          ))}
        </div>
        <div className="sidebar-tenant">
          <div className="tenant-dot"></div>
          <div>
            <div className="tenant-name">Breathe ESG Demo</div>
            <div className="tenant-sub">FY2024 · GB</div>
          </div>
        </div>
      </nav>
      <main className="main-content">{renderPage()}</main>
    </div>
  );
}
