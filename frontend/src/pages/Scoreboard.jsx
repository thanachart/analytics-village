import React, { useState, useEffect } from 'react'
import { api } from '../api'
import { FullWidthTile } from '../components/TileGrid'

export default function Scoreboard() {
  const [episodes, setEpisodes] = useState([])
  const [board, setBoard] = useState([])
  const [selectedEp, setSelectedEp] = useState('')

  useEffect(() => {
    api.listEpisodes().then(eps => {
      setEpisodes(eps)
      if (eps.length > 0) {
        setSelectedEp(eps[0].episode_id)
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedEp) {
      api.getScoreboard(selectedEp).then(setBoard).catch(() => setBoard([]))
    }
  }, [selectedEp])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Scoreboard</h1>
          <p className="page-subtitle">Student rankings and outcomes</p>
        </div>
        <select className="form-select" style={{ width: 250 }} value={selectedEp}
          onChange={e => setSelectedEp(e.target.value)}>
          {episodes.map(ep => (
            <option key={ep.episode_id} value={ep.episode_id}>
              {ep.episode_id} - {ep.title || ep.episode_id}
            </option>
          ))}
        </select>
      </div>

      <div className="tile tile-full">
        <div className="tile-header">
          <span className="tile-label">Rankings</span>
          {board.length > 0 && <span className="tile-badge blue">{board.length} entries</span>}
        </div>
        <div className="tile-body" style={{ padding: 0 }}>
          {board.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Student</th>
                  <th>Score</th>
                  <th>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {board.map(entry => (
                  <tr key={entry.rank}>
                    <td style={{ fontWeight: 700, fontSize: 16 }}>#{entry.rank}</td>
                    <td style={{ fontWeight: 600 }}>{entry.display_name || entry.student_id}</td>
                    <td>
                      <span style={{ fontSize: 18, fontWeight: 300 }}>
                        {entry.final_score?.toFixed(0)}
                      </span>
                      <span style={{ fontSize: 11, color: '#999' }}> / 100</span>
                    </td>
                    <td style={{ fontSize: 12, color: '#888' }}>{entry.submitted_at?.slice(0, 16)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">&#127942;</div>
              <div className="empty-text">No scored submissions yet for this episode</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
