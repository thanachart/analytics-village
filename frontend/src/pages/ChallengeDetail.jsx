import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../api'
import { TileGrid, StatTile, FindingTile, FullWidthTile } from '../components/TileGrid'

export default function ChallengeDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [ep, setEp] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionResult, setActionResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [commitMsg, setCommitMsg] = useState('')
  const [kpis, setKpis] = useState(null)
  const [tables, setTables] = useState([])

  useEffect(() => {
    loadEpisode()
  }, [id])

  async function loadEpisode() {
    setLoading(true)
    try {
      const data = await api.getEpisode(id)
      setEp(data)
      api.getKPIs(id).then(setKpis).catch(() => {})
      api.listTables(id).then(setTables).catch(() => {})
    } catch (e) {
      setEp(null)
    }
    setLoading(false)
  }

  async function doAction(action, label) {
    setBusy(true)
    setActionResult(null)
    try {
      let result
      if (action === 'push') result = await api.pushEpisode(id, commitMsg || null)
      else if (action === 'update') result = await api.updateEpisode(id, commitMsg || null)
      else if (action === 'lock') result = await api.lockEpisode(id)
      else if (action === 'unlock') result = await api.unlockEpisode(id)
      setActionResult({ ok: true, label, ...result })
      loadEpisode()
    } catch (e) {
      setActionResult({ ok: false, label, error: e.message })
    }
    setBusy(false)
  }

  if (loading) return <div style={{ padding: 40, color: '#999' }}>Loading...</div>
  if (!ep) return <div style={{ padding: 40 }}>Episode not found. <Link to="/challenges">Back to challenges</Link></div>

  const isLocked = ep.status === 'closed'
  const isPushed = ep.status === 'active' || ep.github_release_url

  return <div>
    <div className="page-header">
      <div>
        <h1 className="page-title">{ep.episode_id?.toUpperCase()} — {ep.title || 'Challenge'}</h1>
        <p className="page-subtitle">{ep.primary_business} | Tier {ep.tier} | {ep.challenge_type?.replace(/_/g, ' ')}</p>
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span className={`ep-status ${ep.status}`} style={{ fontSize: 11, padding: '4px 14px' }}>{ep.status}</span>
        <Link to="/challenges" className="btn btn-secondary btn-sm">Back</Link>
      </div>
    </div>

    <TileGrid>
      {/* KPIs */}
      <StatTile label="Revenue" value={kpis ? `${(kpis.total_revenue/1000).toFixed(1)}K THB` : '--'} barPct={kpis ? Math.min(100, kpis.total_revenue/1000) : 0} barColor="b" />
      <StatTile label="Transactions" value={kpis ? kpis.total_transactions.toLocaleString() : '--'} barPct={kpis ? Math.min(100, kpis.total_transactions/10) : 0} barColor="g" />
      <StatTile label="Households" value={kpis ? kpis.active_households : '--'} barPct={kpis ? Math.min(100, kpis.active_households) : 0} barColor="b" />
      <StatTile label="Days" value={kpis ? kpis.days_simulated : '--'} barPct={kpis ? Math.min(100, kpis.days_simulated) : 0} barColor="g" />

      {/* GitHub Actions */}
      <FullWidthTile label="GitHub Actions" badge={isLocked ? 'LOCKED' : isPushed ? 'PUSHED' : 'DRAFT'} badgeClass={isLocked ? 'red' : isPushed ? 'green' : 'gray'}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Commit message */}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Commit Message (optional)</label>
            <input className="form-input" value={commitMsg} onChange={e => setCommitMsg(e.target.value)}
              placeholder={`Publish ${ep.episode_id}: ${ep.title || 'challenge data'}`}
              disabled={isLocked} />
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => doAction('push', 'Push to GitHub')}
              disabled={busy || isLocked}>
              {busy ? '...' : 'Push to GitHub'}
            </button>
            <button className="btn btn-secondary" onClick={() => doAction('update', 'Update on GitHub')}
              disabled={busy || isLocked}>
              {busy ? '...' : 'Push Update'}
            </button>

            <div style={{ flex: 1 }} />

            {isLocked ? (
              <button className="btn btn-secondary" onClick={() => doAction('unlock', 'Unlock')} disabled={busy}>
                Unlock Episode
              </button>
            ) : (
              <button className="btn btn-danger" onClick={() => {
                if (confirm('Lock this episode? Submissions will be closed and no further changes pushed.'))
                  doAction('lock', 'Lock')
              }} disabled={busy}>
                Lock Episode
              </button>
            )}
          </div>

          {/* Action result */}
          {actionResult && (
            <div style={{
              padding: 12, borderRadius: 6, fontSize: 12, lineHeight: 1.6,
              background: actionResult.ok ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${actionResult.ok ? '#bbf7d0' : '#fecaca'}`,
              color: actionResult.ok ? '#166534' : '#991b1b',
            }}>
              <strong>{actionResult.label}:</strong> {actionResult.status || actionResult.error || 'Done'}
              {actionResult.commit && <div style={{ marginTop: 4, opacity: .7 }}>{actionResult.commit}</div>}
              {actionResult.url && <div style={{ marginTop: 4 }}><a href={actionResult.url} target="_blank" rel="noopener" style={{ color: '#1d4ed8' }}>{actionResult.url}</a></div>}
            </div>
          )}

          {/* Git status */}
          {ep.git_status && (
            <div style={{ fontSize: 11, color: '#888' }}>
              <div>Remote: <span style={{ fontWeight: 600 }}>{ep.git_status.remote || 'not set'}</span></div>
              {ep.git_status.has_changes && <div style={{ color: '#d97706' }}>Uncommitted changes detected for this episode</div>}
              {ep.git_status.recent_commits?.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  Recent commits:
                  {ep.git_status.recent_commits.map((c, i) => <div key={i} style={{ fontFamily: 'monospace', fontSize: 10 }}>{c}</div>)}
                </div>
              )}
            </div>
          )}
        </div>
      </FullWidthTile>

      {/* Episode Files */}
      <FullWidthTile label="Episode Files" badge={`${ep.files?.length || 0} files`} badgeClass="blue">
        {ep.files?.length > 0 ? (
          <table className="data-table">
            <thead><tr><th>File</th><th>Path</th><th>Size</th><th>Type</th></tr></thead>
            <tbody>
              {ep.files.map((f, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{f.name}</td>
                  <td style={{ fontSize: 11, fontFamily: 'monospace', color: '#888' }}>{f.path}</td>
                  <td>{f.size_kb > 0 ? `${f.size_kb} KB` : '--'}</td>
                  <td><span className={`tile-badge ${f.type === 'db' ? 'blue' : f.type === 'ipynb' ? 'green' : 'gray'}`}>{f.type}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p style={{ color: '#999' }}>No files found for this episode. Generate data first.</p>}
      </FullWidthTile>

      {/* Database Tables */}
      <FullWidthTile label="Database Tables" badge={`${tables.length} tables`} badgeClass="blue">
        {tables.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
            {tables.map(t => (
              <div key={t.name} style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 500 }}>{t.name}</span>
                <span style={{ fontSize: 11, color: t.rows > 0 ? '#1d4ed8' : '#ccc', fontWeight: 600 }}>{t.rows.toLocaleString()}</span>
              </div>
            ))}
          </div>
        ) : <p style={{ color: '#999' }}>No database found.</p>}
      </FullWidthTile>

      {/* Episode Config */}
      <FullWidthTile label="Episode Configuration">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, fontSize: 12 }}>
          <div><span style={{ color: '#999' }}>Episode ID:</span> <strong>{ep.episode_id}</strong></div>
          <div><span style={{ color: '#999' }}>Number:</span> <strong>{ep.episode_number}</strong></div>
          <div><span style={{ color: '#999' }}>Business:</span> <strong>{ep.primary_business}</strong></div>
          <div><span style={{ color: '#999' }}>Tier:</span> <strong>{ep.tier}</strong></div>
          <div><span style={{ color: '#999' }}>Type:</span> <strong>{ep.challenge_type}</strong></div>
          <div><span style={{ color: '#999' }}>Status:</span> <strong>{ep.status}</strong></div>
          <div><span style={{ color: '#999' }}>Created:</span> <strong>{ep.created_at?.slice(0, 16)}</strong></div>
          <div><span style={{ color: '#999' }}>Published:</span> <strong>{ep.published_at?.slice(0, 16) || 'Not yet'}</strong></div>
          <div><span style={{ color: '#999' }}>GitHub:</span> {ep.github_release_url ? <a href={ep.github_release_url} target="_blank" style={{ color: '#1d4ed8' }}>View</a> : <strong>Not pushed</strong>}</div>
        </div>
      </FullWidthTile>
    </TileGrid>
  </div>
}
