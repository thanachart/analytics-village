import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { TileGrid, StatTile, FindingTile, FullWidthTile } from '../components/TileGrid'

export default function ChallengeDetail() {
  const { id } = useParams()
  const [ch, setCh] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionResult, setActionResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [commitMsg, setCommitMsg] = useState('')
  const [kpis, setKpis] = useState(null)
  const [tables, setTables] = useState([])
  const [validation, setValidation] = useState(null)
  const [findings, setFindings] = useState([])
  const [simStatus, setSimStatus] = useState({ status: 'idle' })
  const [regenForm, setRegenForm] = useState({ seed: 42, seed_findings: '' })

  useEffect(() => { loadChallenge() }, [id])

  // Poll sim status when generating
  useEffect(() => {
    if (simStatus.status === 'generating') {
      const t = setInterval(async () => {
        const s = await api.getSimStatus()
        setSimStatus(s)
        if (s.status === 'completed' || s.status === 'error') {
          clearInterval(t)
          loadChallenge()
        }
      }, 2000)
      return () => clearInterval(t)
    }
  }, [simStatus.status])

  async function loadChallenge() {
    setLoading(true)
    try {
      const data = await api.getEpisode(id)
      setCh(data)
      api.getKPIs(id).then(setKpis).catch(() => {})
      api.listTables(id).then(setTables).catch(() => {})
      // Load validation
      fetch(`/api/simulation/validate/${id}`).then(r => r.json()).then(setValidation).catch(() => {})
      // Load findings
      fetch(`/api/simulation/findings/${id}`).then(r => r.json()).then(setFindings).catch(() => setFindings([]))
    } catch { setCh(null) }
    setLoading(false)
  }

  async function doAction(action, label) {
    setBusy(true); setActionResult(null)
    try {
      let result
      if (action === 'push') result = await api.pushEpisode(id, commitMsg || null)
      else if (action === 'update') result = await api.updateEpisode(id, commitMsg || null)
      else if (action === 'lock') result = await api.lockEpisode(id)
      else if (action === 'unlock') result = await api.unlockEpisode(id)
      setActionResult({ ok: true, label, ...result })
      loadChallenge()
    } catch (e) { setActionResult({ ok: false, label, error: e.message }) }
    setBusy(false)
  }

  async function handleRegenerate() {
    if (!confirm('Regenerate data? This will overwrite the current dataset.')) return
    await api.runSimulation({
      challenge_id: id, title: ch?.title || id,
      primary_business: ch?.primary_business || 'supermarket',
      tier: ch?.tier || 1, challenge_type: ch?.challenge_type || 'reporting',
      num_households: 150, history_days: 90, live_days: 0,
      seed: regenForm.seed, use_llm: true,
      seed_findings: regenForm.seed_findings || null, max_retries: 3,
    })
    setSimStatus({ status: 'generating' })
  }

  if (loading) return <div style={{ padding: 40, color: '#999' }}>Loading...</div>
  if (!ch) return <div style={{ padding: 40 }}>Challenge not found. <Link to="/">Back</Link></div>

  const isLocked = ch.status === 'closed'

  return <div>
    <div className="page-header">
      <div>
        <h1 className="page-title">{id.toUpperCase()} — {ch.title || 'Challenge'}</h1>
        <p className="page-subtitle">{ch.primary_business} | Tier {ch.tier} | {ch.challenge_type?.replace(/_/g, ' ')}</p>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <span className={`ep-status ${ch.status}`} style={{ fontSize: 11, padding: '4px 14px' }}>{ch.status}</span>
        <Link to={`/challenges/${id}/dashboard`} className="btn btn-primary btn-sm">Dashboard</Link>
        <Link to="/" className="btn btn-secondary btn-sm">Back</Link>
      </div>
    </div>

    {/* Generation progress */}
    {simStatus.status === 'generating' && (
      <div className="tile tile-full" style={{ marginBottom: 20 }}>
        <div className="tile-header"><span className="tile-label">Generating...</span>
          <span className="tile-badge yellow">{simStatus.progress_pct?.toFixed(0)}%</span></div>
        <div className="tile-body">
          <div className="progress-bar" style={{ marginBottom: 8 }}>
            <div className="progress-fill" style={{ width: `${simStatus.progress_pct || 0}%` }} /></div>
          <p style={{ fontSize: 12, color: '#888' }}>{simStatus.message}</p>
        </div>
      </div>
    )}

    <TileGrid>
      {/* KPIs */}
      <StatTile label="Revenue" value={kpis ? `${(kpis.total_revenue/1000).toFixed(1)}K` : '--'} barPct={kpis ? Math.min(100, kpis.total_revenue/20000) : 0} barColor="b" />
      <StatTile label="Transactions" value={kpis ? kpis.total_transactions.toLocaleString() : '--'} barPct={kpis ? Math.min(100, kpis.total_transactions/100) : 0} barColor="g" />
      <StatTile label="Households" value={kpis ? kpis.active_households : '--'} barColor="b" />
      <StatTile label="Avg Basket" value={kpis ? `${kpis.avg_basket_thb.toFixed(0)} THB` : '--'} barColor="b" />

      {/* Data Validation */}
      <FullWidthTile label="Data Quality Validation"
        badge={validation ? (validation.passed ? 'PASSED' : 'ISSUES') : 'NOT RUN'}
        badgeClass={validation?.passed ? 'green' : validation ? 'red' : 'gray'}>
        {validation ? (
          <div>
            <p style={{ fontSize: 12, color: '#555', marginBottom: 12 }}>{validation.summary}</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
              {validation.checks?.map((c, i) => (
                <div key={i} style={{ padding: '8px 12px', borderRadius: 6, fontSize: 12,
                  background: c.passed ? '#f0fdf4' : '#fef2f2',
                  border: `1px solid ${c.passed ? '#bbf7d0' : '#fecaca'}` }}>
                  <span style={{ fontWeight: 600, color: c.passed ? '#166534' : '#991b1b' }}>
                    {c.passed ? '+' : 'X'} {c.name}
                  </span>
                  <div style={{ color: '#666', marginTop: 2 }}>{c.message}</div>
                  <div style={{ color: '#999', fontSize: 10 }}>Range: {c.range} | Value: {c.value}</div>
                </div>
              ))}
            </div>
          </div>
        ) : <p style={{ color: '#999' }}>Generate data to see validation results.</p>}
      </FullWidthTile>

      {/* Key Findings */}
      <FullWidthTile label="Key Findings (LLM)" badge={`${findings.length} findings`} badgeClass={findings.length > 0 ? 'blue' : 'gray'}>
        {findings.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {findings.map((f, i) => (
              <div key={i} className="act-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span className={`tile-badge ${f.severity === 'high' ? 'red' : f.severity === 'medium' ? 'yellow' : 'blue'}`}>{f.severity}</span>
                  <span style={{ fontSize: 9, color: '#999', textTransform: 'uppercase', letterSpacing: 1 }}>{f.category}</span>
                </div>
                <div className="ac-title">{f.title}</div>
                <div className="ac-desc">{f.description}</div>
                {f.evidence && <div style={{ fontSize: 10, color: '#888', fontStyle: 'italic' }}>{f.evidence}</div>}
              </div>
            ))}
          </div>
        ) : <p style={{ color: '#999' }}>No findings yet. Enable LLM when generating or click "Generate Findings" below.</p>}
      </FullWidthTile>

      {/* Regenerate */}
      <FullWidthTile label="Regenerate Data">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="form-row">
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Seed</label>
              <input className="form-input" type="number" value={regenForm.seed} onChange={e => setRegenForm(f => ({ ...f, seed: +e.target.value }))} />
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Seed Findings (guide LLM analysis)</label>
              <input className="form-input" value={regenForm.seed_findings} onChange={e => setRegenForm(f => ({ ...f, seed_findings: e.target.value }))}
                placeholder="e.g. stockout impact, payday patterns" />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-danger" onClick={handleRegenerate} disabled={simStatus.status === 'generating'}>
              Regenerate Data (with validation + retry)
            </button>
          </div>
        </div>
      </FullWidthTile>

      {/* GitHub Actions */}
      <FullWidthTile label="GitHub Actions" badge={isLocked ? 'LOCKED' : ch.status === 'active' ? 'PUSHED' : 'DRAFT'}
        badgeClass={isLocked ? 'red' : ch.status === 'active' ? 'green' : 'gray'}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Commit Message</label>
            <input className="form-input" value={commitMsg} onChange={e => setCommitMsg(e.target.value)}
              placeholder={`Publish ${id}: ${ch.title || 'challenge'}`} disabled={isLocked} />
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-primary" onClick={() => doAction('push', 'Push')} disabled={busy || isLocked}>Push to GitHub</button>
            <button className="btn btn-secondary" onClick={() => doAction('update', 'Update')} disabled={busy || isLocked}>Push Update</button>
            <div style={{ flex: 1 }} />
            {isLocked
              ? <button className="btn btn-secondary" onClick={() => doAction('unlock', 'Unlock')} disabled={busy}>Unlock</button>
              : <button className="btn btn-danger" onClick={() => confirm('Lock this challenge?') && doAction('lock', 'Lock')} disabled={busy}>Lock</button>}
          </div>
          {actionResult && (
            <div style={{ padding: 10, borderRadius: 6, fontSize: 12,
              background: actionResult.ok ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${actionResult.ok ? '#bbf7d0' : '#fecaca'}` }}>
              <strong>{actionResult.label}:</strong> {actionResult.status || actionResult.error}
              {actionResult.url && <div><a href={actionResult.url} target="_blank" style={{ color: '#1d4ed8' }}>{actionResult.url}</a></div>}
            </div>
          )}
          {ch.git_status && (
            <div style={{ fontSize: 11, color: '#888' }}>
              Remote: {ch.git_status.remote || 'not set'}
              {ch.git_status.recent_commits?.map((c, i) => <div key={i} style={{ fontFamily: 'monospace', fontSize: 10 }}>{c}</div>)}
            </div>
          )}
        </div>
      </FullWidthTile>

      {/* Files */}
      <FullWidthTile label="Challenge Files" badge={`${ch.files?.length || 0}`} badgeClass="blue">
        {ch.files?.length > 0 ? (
          <table className="data-table"><thead><tr><th>File</th><th>Path</th><th>Size</th></tr></thead>
            <tbody>{ch.files.map((f, i) => (
              <tr key={i}><td style={{ fontWeight: 600 }}>{f.name}</td>
                <td style={{ fontSize: 11, fontFamily: 'monospace', color: '#888' }}>{f.path}</td>
                <td>{f.size_kb > 0 ? `${f.size_kb} KB` : '--'}</td></tr>
            ))}</tbody></table>
        ) : <p style={{ color: '#999' }}>No files yet.</p>}
      </FullWidthTile>

      {/* Database tables */}
      {tables.length > 0 && (
        <FullWidthTile label="Database Tables" badge={`${tables.length}`} badgeClass="blue">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
            {tables.map(t => (
              <div key={t.name} style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 6, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 12 }}>{t.name}</span>
                <span style={{ fontSize: 11, color: t.rows > 0 ? '#1d4ed8' : '#ccc', fontWeight: 600 }}>{t.rows.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </FullWidthTile>
      )}
    </TileGrid>
  </div>
}
