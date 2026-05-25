import React, { useState, useCallback } from 'react';
import { importAPI } from '../api';

const SOURCES = [
  {
    id: 'sap',
    label: 'SAP Data',
    subtitle: 'Fuel & Procurement',
    icon: '⬡',
    desc: 'SAP CSV exports — German column headers, mixed units, plant codes',
    examples: ['Diesel/petrol consumption', 'Procurement purchases', 'Plant-level fuel data'],
    format: 'CSV (SAP export, supports German headers)',
  },
  {
    id: 'utility',
    label: 'Utility / Electricity',
    subtitle: 'Grid & Meter Data',
    icon: '⚡',
    desc: 'Electricity billing CSV from utility portals (UK Power Networks, Octopus, etc.)',
    examples: ['Monthly kWh consumption', 'Meter readings by site', 'Billing period data'],
    format: 'CSV (utility portal export)',
  },
  {
    id: 'travel',
    label: 'Corporate Travel',
    subtitle: 'Concur / Navan Export',
    icon: '✈',
    desc: 'Business travel data from expense/travel management platforms',
    examples: ['Flights (IATA codes)', 'Hotel nights', 'Ground transport / taxis'],
    format: 'CSV (Concur / Navan export)',
  },
];

export default function ImportPage({ onImportComplete }) {
  const [selectedSource, setSelectedSource] = useState(null);
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }, []);

  const handleUpload = async () => {
    if (!selectedSource || !file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await importAPI.uploadFile(selectedSource, file);
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.error || 'Upload failed. Check the file format.');
    } finally {
      setLoading(false);
    }
  };

  const handleSample = async (source) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await importAPI.generateSample(source);
      setResult({ ...res.data, isSample: true });
    } catch (e) {
      setError(e.response?.data?.error || 'Failed to generate sample data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page import-page">
      <div className="page-header">
        <div>
          <h1>Import Data</h1>
          <p className="page-sub">Upload CSVs from your business systems or load sample data to explore</p>
        </div>
      </div>

      {/* Source selector */}
      <div className="source-grid">
        {SOURCES.map(s => (
          <div
            key={s.id}
            className={`source-card ${selectedSource === s.id ? 'selected' : ''}`}
            onClick={() => setSelectedSource(s.id)}
          >
            <div className="source-card-header">
              <span className="source-card-icon">{s.icon}</span>
              <div>
                <div className="source-card-title">{s.label}</div>
                <div className="source-card-sub">{s.subtitle}</div>
              </div>
              {selectedSource === s.id && <span className="source-check">✓</span>}
            </div>
            <p className="source-card-desc">{s.desc}</p>
            <ul className="source-examples">
              {s.examples.map((ex, i) => <li key={i}>{ex}</li>)}
            </ul>
            <div className="source-format">{s.format}</div>
            <button
              className="btn btn-outline btn-sm sample-btn"
              onClick={(e) => { e.stopPropagation(); handleSample(s.id); }}
              disabled={loading}
            >
              ⊕ Load sample data
            </button>
          </div>
        ))}
      </div>

      {/* File upload */}
      {selectedSource && (
        <div className="upload-section">
          <h3>Upload {SOURCES.find(s => s.id === selectedSource)?.label} File</h3>

          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById('file-input').click()}
          >
            <input
              id="file-input"
              type="file"
              accept=".csv,.txt,.xlsx"
              style={{ display: 'none' }}
              onChange={(e) => setFile(e.target.files[0])}
            />
            {file ? (
              <div className="file-selected">
                <span className="file-icon">📄</span>
                <div>
                  <div className="file-name">{file.name}</div>
                  <div className="file-size">{(file.size / 1024).toFixed(1)} KB</div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); setFile(null); }}>✕</button>
              </div>
            ) : (
              <div className="drop-prompt">
                <div className="drop-icon">↑</div>
                <div>Drop CSV file here or click to browse</div>
                <div className="drop-sub">Supports CSV, TXT, XLSX</div>
              </div>
            )}
          </div>

          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!file || loading}
          >
            {loading ? '⏳ Processing...' : '↑ Import & Normalize'}
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="processing-card">
          <div className="spinner"></div>
          <div>
            <div>Normalizing data...</div>
            <div className="processing-sub">Cleaning columns, converting units, calculating CO₂e</div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="alert alert-error">
          <strong>Import failed:</strong> {error}
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="result-card">
          <div className="result-header">
            <span className="result-icon">✓</span>
            <div>
              <div className="result-title">{result.isSample ? 'Sample data loaded' : 'Import complete'}</div>
              <div className="result-sub">{result.message || `${result.successful_rows} records normalized`}</div>
            </div>
          </div>
          <div className="result-stats">
            <div className="result-stat">
              <span>{result.total_rows || result.successful_rows || '—'}</span>
              <label>Total rows</label>
            </div>
            <div className="result-stat">
              <span className="green">{result.successful_rows || '—'}</span>
              <label>Successful</label>
            </div>
            <div className="result-stat">
              <span className="amber">{result.suspicious_rows || result.suspicious || 0}</span>
              <label>Suspicious</label>
            </div>
            <div className="result-stat">
              <span className="red">{result.failed_rows || 0}</span>
              <label>Failed</label>
            </div>
          </div>
          <button className="btn btn-primary" onClick={onImportComplete}>
            Review Records →
          </button>
        </div>
      )}

      {/* Data quality explainer */}
      <div className="info-card">
        <h4>How normalization works</h4>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-icon">🗂</span>
            <div>
              <strong>Column detection</strong>
              <p>German SAP headers (Buchungsdatum, Menge, Werk) auto-mapped to standard fields</p>
            </div>
          </div>
          <div className="info-item">
            <span className="info-icon">⚖</span>
            <div>
              <strong>Unit normalization</strong>
              <p>Gallons→litres, miles→km, MWh→kWh — all converted to canonical units</p>
            </div>
          </div>
          <div className="info-item">
            <span className="info-icon">🌍</span>
            <div>
              <strong>CO₂e calculation</strong>
              <p>DEFRA emission factors applied per category: diesel 2.68 kgCO₂e/L, UK grid 0.233 kgCO₂e/kWh</p>
            </div>
          </div>
          <div className="info-item">
            <span className="info-icon">⚑</span>
            <div>
              <strong>Anomaly detection</strong>
              <p>Zero quantities, outliers, missing dates, negative reversals flagged automatically</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
