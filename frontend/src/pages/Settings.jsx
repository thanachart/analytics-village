import React, { useState } from 'react'
import { FullWidthTile } from '../components/TileGrid'

export default function Settings() {
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434/v1')
  const [model, setModel] = useState('gemma4:e2b')
  const [maxConcurrent, setMaxConcurrent] = useState(8)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure LLM, scoring, and preferences</p>
        </div>
      </div>

      <div className="tile tile-full" style={{ marginBottom: 20 }}>
        <div className="tile-header"><span className="tile-label">LLM Configuration</span></div>
        <div className="tile-body">
          <div className="form-row" style={{ marginBottom: 16 }}>
            <div className="form-group">
              <label className="form-label">Ollama Base URL</label>
              <input className="form-input" value={ollamaUrl} onChange={e => setOllamaUrl(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Model</label>
              <input className="form-input" value={model} onChange={e => setModel(e.target.value)} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Max Concurrent LLM Calls</label>
              <input className="form-input" type="number" min="1" max="32" value={maxConcurrent} onChange={e => setMaxConcurrent(+e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Connection Status</label>
              <div style={{ padding: '10px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className="status-dot ok" />
                <span style={{ fontSize: 12, color: '#16a34a' }}>Connected</span>
              </div>
            </div>
          </div>
          <button className="btn btn-secondary" style={{ marginTop: 8 }}>Test Connection</button>
        </div>
      </div>

      <div className="tile tile-full" style={{ marginBottom: 20 }}>
        <div className="tile-header"><span className="tile-label">Scoring Defaults</span></div>
        <div className="tile-body">
          <table className="data-table">
            <thead>
              <tr><th>Tier</th><th>Finding</th><th>Method</th><th>Recommendation</th><th>Communication</th><th>Risk</th></tr>
            </thead>
            <tbody>
              <tr><td>Tier 1 - Reporting</td><td>35%</td><td>20%</td><td>25%</td><td>15%</td><td>5%</td></tr>
              <tr><td>Tier 2 - Analysis</td><td>30%</td><td>25%</td><td>25%</td><td>10%</td><td>10%</td></tr>
              <tr><td>Tier 3 - ML</td><td>25%</td><td>30%</td><td>25%</td><td>10%</td><td>10%</td></tr>
              <tr><td>Tier 4 - Advanced</td><td>25%</td><td>25%</td><td>30%</td><td>10%</td><td>10%</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="tile tile-full">
        <div className="tile-header"><span className="tile-label">Display Preferences</span></div>
        <div className="tile-body">
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Currency</label>
              <input className="form-input" value="THB (Thai Baht)" disabled />
            </div>
            <div className="form-group">
              <label className="form-label">Timezone</label>
              <input className="form-input" value="Asia/Bangkok" disabled />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
