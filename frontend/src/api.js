const BASE = '/api'

async function fetchJSON(url, options = {}) {
  const resp = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!resp.ok) throw new Error(`API ${resp.status}: ${resp.statusText}`)
  return resp.json()
}

export const api = {
  health: () => fetchJSON('/health'),

  // Episodes
  listEpisodes: (status) => fetchJSON('/episodes' + (status ? `?status=${status}` : '')),
  getEpisode: (id) => fetchJSON(`/episodes/${id}`),
  createEpisode: (data) => fetchJSON('/episodes', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id, status) => fetchJSON(`/episodes/${id}/status?status=${status}`, { method: 'PUT' }),
  deleteEpisode: (id) => fetchJSON(`/episodes/${id}`, { method: 'DELETE' }),

  // GitHub actions
  pushEpisode: (id, msg) => fetchJSON(`/episodes/${id}/push`, { method: 'POST', body: JSON.stringify({ commit_message: msg }) }),
  updateEpisode: (id, msg) => fetchJSON(`/episodes/${id}/update`, { method: 'POST', body: JSON.stringify({ commit_message: msg }) }),
  lockEpisode: (id) => fetchJSON(`/episodes/${id}/lock`, { method: 'POST' }),
  unlockEpisode: (id) => fetchJSON(`/episodes/${id}/unlock`, { method: 'POST' }),

  // Simulation
  runSimulation: (data) => fetchJSON('/simulation/run', { method: 'POST', body: JSON.stringify(data) }),
  getSimStatus: () => fetchJSON('/simulation/status'),
  getKPIs: (epId) => fetchJSON('/simulation/kpis' + (epId ? `?episode_id=${epId}` : '')),

  // Data
  dailyRevenue: (epId, biz) => fetchJSON(`/data/daily-revenue?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  customerSummary: (epId, biz) => fetchJSON(`/data/customer-summary?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  topSkus: (epId, biz, n) => fetchJSON(`/data/top-skus?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}&limit=${n || 15}`),
  lifecycleSummary: (epId, biz) => fetchJSON(`/data/lifecycle-summary?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  stockoutImpact: (epId, biz) => fetchJSON(`/data/stockout-impact?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  dayOfWeek: (epId, biz) => fetchJSON(`/data/day-of-week?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  listTables: (epId) => fetchJSON(`/data/tables${epId ? `?episode_id=${epId}` : ''}`),
  tablePreview: (t, epId, n) => fetchJSON(`/data/table-preview/${t}?${epId ? `episode_id=${epId}&` : ''}limit=${n || 50}`),

  // Submissions
  listSubmissions: (epId) => fetchJSON('/submissions' + (epId ? `?episode_id=${epId}` : '')),
  getSubmission: (id) => fetchJSON(`/submissions/${id}`),
  scoreSubmission: (id, data) => fetchJSON(`/submissions/${id}/score`, { method: 'POST', body: JSON.stringify(data) }),
  getScoreboard: (epId) => fetchJSON(`/submissions/scoreboard/${epId}`),

  // Export
  exportDbUrl: (id) => `${BASE}/export/village-db/${id}`,
}
