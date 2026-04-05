import React from 'react'

export function TileGrid({ children }) {
  return <div className="wall-grid">{children}</div>
}

export function StatTile({ label, value, delta, deltaColor = 'g', barPct = 0, barColor = 'b' }) {
  return (
    <div className="tile tile-stat">
      <div className="tile-header"><span className="tile-label">{label}</span></div>
      <div className="tile-body">
        <div className="stat-num">{value}</div>
        {delta && <div className={`stat-delta ${deltaColor}`}>{delta}</div>}
        {barPct > 0 && (
          <div className="stat-bar">
            <div className={`stat-fill ${barColor}`} style={{ width: `${Math.min(100, barPct)}%` }} />
          </div>
        )}
      </div>
    </div>
  )
}

export function FindingTile({ label, text, badge, badgeClass = 'blue', span = 7 }) {
  const cls = span === 12 ? 'tile-full' : span === 7 ? 'tile-finding' : `tile-half`
  return (
    <div className={`tile ${cls}`}>
      <div className="tile-header">
        <span className="tile-label">{label}</span>
        {badge && <span className={`tile-badge ${badgeClass}`}>{badge}</span>}
      </div>
      <div className="tile-body">
        <div className="finding-text">{text}</div>
      </div>
    </div>
  )
}

export function ChartTile({ label, children, span = 5 }) {
  const cls = span === 12 ? 'tile-full' : span === 5 ? 'tile-chart' : 'tile-half'
  return (
    <div className={`tile ${cls}`}>
      <div className="tile-header"><span className="tile-label">{label}</span></div>
      <div className="tile-body">
        <div className="chart-inner">{children}</div>
      </div>
    </div>
  )
}

export function FullWidthTile({ label, badge, badgeClass, children }) {
  return (
    <div className="tile tile-full">
      <div className="tile-header">
        <span className="tile-label">{label}</span>
        {badge && <span className={`tile-badge ${badgeClass || 'gray'}`}>{badge}</span>}
      </div>
      <div className="tile-body">{children}</div>
    </div>
  )
}
