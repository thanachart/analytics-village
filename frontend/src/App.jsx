import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Challenges from './pages/Challenges'
import Submissions from './pages/Submissions'
import Scoreboard from './pages/Scoreboard'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="challenges" element={<Challenges />} />
          <Route path="submissions" element={<Submissions />} />
          <Route path="scoreboard" element={<Scoreboard />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
