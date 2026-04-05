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
  // Health
  health: () => fetchJSON('/health'),

  // Episodes
  listEpisodes: (status) => fetchJSON('/episodes' + (status ? `?status=${status}` : '')),
  getEpisode: (id) => fetchJSON(`/episodes/${id}`),
  createEpisode: (data) => fetchJSON('/episodes', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id, status) => fetchJSON(`/episodes/${id}/status?status=${status}`, { method: 'PUT' }),

  // Simulation
  runSimulation: (data) => fetchJSON('/simulation/run', { method: 'POST', body: JSON.stringify(data) }),
  getSimStatus: () => fetchJSON('/simulation/status'),
  getKPIs: (episodeId) => fetchJSON('/simulation/kpis' + (episodeId ? `?episode_id=${episodeId}` : '')),

  // Data exploration
  dailyRevenue: (epId, biz) => fetchJSON(`/data/daily-revenue?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  customerSummary: (epId, biz) => fetchJSON(`/data/customer-summary?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  topSkus: (epId, biz, limit) => fetchJSON(`/data/top-skus?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}&limit=${limit || 15}`),
  lifecycleSummary: (epId, biz) => fetchJSON(`/data/lifecycle-summary?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  stockoutImpact: (epId, biz) => fetchJSON(`/data/stockout-impact?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  dayOfWeek: (epId, biz) => fetchJSON(`/data/day-of-week?${epId ? `episode_id=${epId}&` : ''}business_id=${biz || 'supermarket'}`),
  tablePreview: (table, epId, limit) => fetchJSON(`/data/table-preview/${table}?${epId ? `episode_id=${epId}&` : ''}limit=${limit || 50}`),
  listTables: (epId) => fetchJSON(`/data/tables${epId ? `?episode_id=${epId}` : ''}`),

  // Submissions
  listSubmissions: (episodeId) => fetchJSON('/submissions' + (episodeId ? `?episode_id=${episodeId}` : '')),
  getSubmission: (id) => fetchJSON(`/submissions/${id}`),
  scoreSubmission: (id, data) => fetchJSON(`/submissions/${id}/score`, { method: 'POST', body: JSON.stringify(data) }),
  getScoreboard: (episodeId) => fetchJSON(`/submissions/scoreboard/${episodeId}`),

  // Export
  exportDbUrl: (id) => `${BASE}/export/village-db/${id}`,
  exportBriefUrl: (id) => `${BASE}/export/brief/${id}`,
}
