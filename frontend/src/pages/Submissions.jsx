import React, { useState, useEffect } from 'react'
import { api } from '../api'
import { FullWidthTile } from '../components/TileGrid'

export default function Submissions() {
  const [submissions, setSubmissions] = useState([])
  const [episodes, setEpisodes] = useState([])
  const [selectedEp, setSelectedEp] = useState('')

  useEffect(() => {
    api.listEpisodes().then(setEpisodes).catch(() => {})
    api.listSubmissions().then(setSubmissions).catch(() => {})
  }, [])

  const filtered = selectedEp
    ? submissions.filter(s => s.episode_id === selectedEp)
    : submissions

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Submissions</h1>
          <p className="page-subtitle">Review and score student submissions</p>
        </div>
      </div>

      <div style={{ marginBottom: 20, display: 'flex', gap: 12 }}>
        <select className="form-select" style={{ width: 250 }} value={selectedEp}
          onChange={e => setSelectedEp(e.target.value)}>
          <option value="">All episodes</option>
          {episodes.map(ep => (
            <option key={ep.episode_id} value={ep.episode_id}>
              {ep.episode_id} - {ep.title || ep.episode_id}
            </option>
          ))}
        </select>
        <span style={{ fontSize: 12, color: '#888', alignSelf: 'center' }}>
          {filtered.length} submission{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="tile tile-full">
        <div className="tile-header">
          <span className="tile-label">Submissions</span>
          <span className="tile-badge blue">{filtered.length}</span>
        </div>
        <div className="tile-body" style={{ padding: 0 }}>
          {filtered.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Episode</th>
                  <th>Submitted</th>
                  <th>Status</th>
                  <th>Auto Score</th>
                  <th>Final Score</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(s => (
                  <tr key={s.submission_id}>
                    <td style={{ fontWeight: 600 }}>{s.student_id}</td>
                    <td>{s.episode_id}</td>
                    <td style={{ fontSize: 12, color: '#888' }}>{s.submitted_at?.slice(0, 16)}</td>
                    <td>
                      <span className={`tile-badge ${s.validation_status === 'valid' ? 'green' : 'red'}`}>
                        {s.validation_status}
                      </span>
                    </td>
                    <td>{s.auto_score ?? '--'}</td>
                    <td style={{ fontWeight: 600 }}>{s.final_score ?? '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">&#128203;</div>
              <div className="empty-text">No submissions yet</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
