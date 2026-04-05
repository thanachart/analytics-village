import React, { useState, useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../api'

const NAV_ITEMS = [
  { to: '/', icon: '~', label: 'Dashboard' },
  { to: '/challenges', icon: '!', label: 'Challenges' },
  { to: '/submissions', icon: '#', label: 'Submissions' },
  { to: '/scoreboard', icon: '*', label: 'Scoreboard' },
  { to: '/settings', icon: '%', label: 'Settings' },
]

export default function Layout() {
  const [simStatus, setSimStatus] = useState({ status: 'idle', message: '' })

  useEffect(() => {
    const poll = setInterval(async () => {
      try {
        const s = await api.getSimStatus()
        setSimStatus(s)
      } catch {}
    }, 3000)
    return () => clearInterval(poll)
  }, [])

  const dotClass = simStatus.status === 'generating' ? 'busy'
    : simStatus.status === 'error' ? 'err' : 'ok'

  return (
    <div className="app-layout">
      <header className="app-topbar">
        <span className="app-brand">
          <span className="app-brand-icon">&#9961;</span>
          Analytics Village
        </span>
        <div className="topbar-sep" />
        <span style={{ fontSize: 12, color: '#888' }}>Facilitator</span>
        <div className="topbar-status">
          <div className={`status-dot ${dotClass}`} />
          <span className="status-label">
            {simStatus.status === 'generating' ? `Generating... ${simStatus.progress_pct?.toFixed(0)}%` : simStatus.status}
          </span>
        </div>
      </header>
      <div className="app-body">
        <nav className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-label">Navigation</div>
            <ul className="sidebar-nav">
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </ul>
          </div>
          <div className="sidebar-footer">
            <div className="sim-status">
              <div className={`sim-status-dot status-dot ${dotClass}`} />
              <span className="sim-status-text">
                {simStatus.status === 'idle' ? 'Sim Ready' :
                 simStatus.status === 'generating' ? 'Generating...' :
                 simStatus.status === 'completed' ? 'Complete' : simStatus.status}
              </span>
            </div>
          </div>
        </nav>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
