import React, { useState, useEffect } from 'react'
import { api } from '../api'
import { TileGrid, FullWidthTile } from '../components/TileGrid'

const CHALLENGE_TYPES = [
  'reporting', 'retention', 'inventory', 'cohort_churn',
  'forecasting', 'segmentation', 'recommendation',
  'anomaly', 'nlp', 'strategy'
]

export default function Challenges() {
  const [episodes, setEpisodes] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [simStatus, setSimStatus] = useState({ status: 'idle' })
  const [form, setForm] = useState({
    title: '', episode_number: 1, primary_business: 'supermarket',
    tier: 1, challenge_type: 'reporting',
    num_households: 150, history_days: 90, live_days: 0,
    seed: 42, use_llm: false,
  })

  useEffect(() => {
    api.listEpisodes().then(setEpisodes).catch(() => {})
  }, [])

  useEffect(() => {
    if (simStatus.status === 'generating') {
      const t = setInterval(async () => {
        const s = await api.getSimStatus()
        setSimStatus(s)
        if (s.status === 'completed' || s.status === 'error') {
          clearInterval(t)
          api.listEpisodes().then(setEpisodes)
        }
      }, 2000)
      return () => clearInterval(t)
    }
  }, [simStatus.status])

  const handleGenerate = async () => {
    const epId = `ep${String(form.episode_number).padStart(2, '0')}`
    await api.runSimulation({
      episode_id: epId,
      num_households: form.num_households,
      history_days: form.history_days,
      live_days: form.use_llm ? form.live_days : 0,
      seed: form.seed,
      use_llm: form.use_llm,
      primary_business: form.primary_business,
    })
    setSimStatus({ status: 'generating' })
    setShowForm(false)
  }

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Challenges</h1>
          <p className="page-subtitle">Manage episodes and generate new challenges</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ New Challenge'}
        </button>
      </div>

      {simStatus.status === 'generating' && (
        <div className="tile tile-full" style={{ marginBottom: 20 }}>
          <div className="tile-header">
            <span className="tile-label">Generating...</span>
            <span className="tile-badge yellow">{simStatus.progress_pct?.toFixed(0)}%</span>
          </div>
          <div className="tile-body">
            <div className="progress-bar" style={{ marginBottom: 8 }}>
              <div className="progress-fill" style={{ width: `${simStatus.progress_pct || 0}%` }} />
            </div>
            <p style={{ fontSize: 12, color: '#888' }}>{simStatus.message}</p>
          </div>
        </div>
      )}

      {showForm && (
        <div className="tile tile-full" style={{ marginBottom: 24 }}>
          <div className="tile-header"><span className="tile-label">New Challenge Configuration</span></div>
          <div className="tile-body">
            <div className="form-row" style={{ marginBottom: 16 }}>
              <div className="form-group">
                <label className="form-label">Episode Title</label>
                <input className="form-input" value={form.title} onChange={e => set('title', e.target.value)} placeholder="e.g. Open for Business" />
              </div>
              <div className="form-group">
                <label className="form-label">Episode Number</label>
                <input className="form-input" type="number" min="1" max="20" value={form.episode_number} onChange={e => set('episode_number', +e.target.value)} />
              </div>
            </div>
            <div className="form-row" style={{ marginBottom: 16 }}>
              <div className="form-group">
                <label className="form-label">Primary Business</label>
                <select className="form-select" value={form.primary_business} onChange={e => set('primary_business', e.target.value)}>
                  <option value="supermarket">Village Fresh Supermarket</option>
                  <option value="pharmacy">P'Noi Pharmacy</option>
                  <option value="coffee_shop">Village Coffee & Bakery</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Challenge Type</label>
                <select className="form-select" value={form.challenge_type} onChange={e => set('challenge_type', e.target.value)}>
                  {CHALLENGE_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
            </div>
            <div className="form-row-3" style={{ marginBottom: 16 }}>
              <div className="form-group">
                <label className="form-label">Households</label>
                <input className="form-input" type="number" min="20" max="500" value={form.num_households} onChange={e => set('num_households', +e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">History Days</label>
                <input className="form-input" type="number" min="7" max="365" value={form.history_days} onChange={e => set('history_days', +e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Seed</label>
                <input className="form-input" type="number" value={form.seed} onChange={e => set('seed', +e.target.value)} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20 }}>
              <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={form.use_llm} onChange={e => set('use_llm', e.target.checked)} />
                Enable LLM (Ollama) for persona seeding + live simulation
              </label>
              {form.use_llm && (
                <div className="form-group" style={{ margin: 0, width: 120 }}>
                  <input className="form-input" type="number" min="0" max="90" value={form.live_days} onChange={e => set('live_days', +e.target.value)} placeholder="Live days" />
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="btn btn-primary btn-lg" onClick={handleGenerate}>Generate Challenge</button>
              <button className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <TileGrid>
        {episodes.length > 0 ? episodes.map(ep => (
          <div key={ep.episode_id} className="tile tile-third">
            <div className="tile-body">
              <div className="ep-number">{ep.episode_id}</div>
              <div className="ep-title">{ep.title || ep.episode_id.toUpperCase()}</div>
              <div className="ep-meta">
                {ep.primary_business} &middot; Tier {ep.tier}<br/>
                {ep.challenge_type?.replace(/_/g, ' ')}
              </div>
              <span className={`ep-status ${ep.status}`}>{ep.status}</span>
            </div>
          </div>
        )) : (
          <div className="tile tile-full">
            <div className="tile-body">
              <div className="empty-state">
                <div className="empty-icon">&#127968;</div>
                <div className="empty-text">No challenges yet. Click "New Challenge" to generate your first episode.</div>
              </div>
            </div>
          </div>
        )}
      </TileGrid>
    </div>
  )
}
