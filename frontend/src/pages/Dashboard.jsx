import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Filler, Legend } from 'chart.js'
import { api } from '../api'
import { TileGrid, StatTile, FindingTile, ChartTile, FullWidthTile } from '../components/TileGrid'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Filler, Legend)

const CHART_OPTS = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }

export default function Dashboard() {
  const [kpis, setKpis] = useState(null)
  const [episodes, setEpisodes] = useState([])
  const [revenue, setRevenue] = useState([])
  const [topSkus, setTopSkus] = useState([])
  const [dowData, setDowData] = useState([])
  const [lifecycle, setLifecycle] = useState(null)
  const [customers, setCustomers] = useState([])
  const [stockouts, setStockouts] = useState([])

  useEffect(() => {
    api.getKPIs().then(setKpis).catch(() => {})
    api.listEpisodes().then(setEpisodes).catch(() => {})
    api.dailyRevenue().then(setRevenue).catch(() => {})
    api.topSkus(null, null, 10).then(setTopSkus).catch(() => {})
    api.dayOfWeek().then(setDowData).catch(() => {})
    api.lifecycleSummary().then(setLifecycle).catch(() => {})
    api.customerSummary().then(setCustomers).catch(() => {})
    api.stockoutImpact().then(setStockouts).catch(() => {})
  }, [])

  const fmtThb = (n) => n >= 1000 ? `${(n/1000).toFixed(1)}K` : `${Math.round(n)}`

  // Revenue chart
  const revChart = {
    labels: revenue.map(r => `Day ${r.day}`),
    datasets: [{
      label: 'Revenue (THB)',
      data: revenue.map(r => r.revenue),
      borderColor: '#1d4ed8',
      backgroundColor: 'rgba(29,78,216,0.06)',
      fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5,
    }]
  }

  // Day of week chart
  const dowChart = {
    labels: dowData.map(d => d.day_of_week?.slice(0, 3).toUpperCase()),
    datasets: [{
      label: 'Revenue',
      data: dowData.map(d => d.revenue),
      backgroundColor: dowData.map((_, i) => i === 5 ? '#1d4ed8' : '#bfdbfe'),
      borderRadius: 4,
    }]
  }

  // Lifecycle donut
  const lcColors = { retained: '#22c55e', at_risk: '#f59e0b', churned: '#ef4444', aware: '#60a5fa', unaware: '#d1d5db', new_acquisition: '#34d399', winback_candidate: '#a78bfa', dormant: '#9ca3af' }
  const lcChart = lifecycle?.states ? {
    labels: lifecycle.states.map(s => s.lifecycle_state),
    datasets: [{
      data: lifecycle.states.map(s => s.count),
      backgroundColor: lifecycle.states.map(s => lcColors[s.lifecycle_state] || '#d1d5db'),
      borderWidth: 0,
    }]
  } : null

  // Top SKU bar chart
  const skuChart = {
    labels: topSkus.slice(0, 8).map(s => s.sku_name?.length > 18 ? s.sku_name.slice(0, 18) + '...' : s.sku_name),
    datasets: [{
      label: 'Revenue (THB)',
      data: topSkus.slice(0, 8).map(s => s.revenue),
      backgroundColor: '#1d4ed8',
      borderRadius: 4,
    }]
  }

  // Insights
  const topCustomer = customers[0]
  const totalStockoutLoss = stockouts.reduce((s, r) => s + (r.revenue_lost || 0), 0)
  const peakDay = dowData.reduce((max, d) => d.revenue > (max?.revenue || 0) ? d : max, null)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Analytics Village — Village economy at a glance</p>
        </div>
        <Link to="/challenges" className="btn btn-primary">+ New Challenge</Link>
      </div>

      <TileGrid>
        {/* KPI Row */}
        <StatTile label="Total Revenue" value={kpis ? `${fmtThb(kpis.total_revenue)} THB` : '--'}
          delta={kpis ? `${kpis.days_simulated} days simulated` : ''} deltaColor="g"
          barPct={kpis ? Math.min(100, kpis.total_revenue / 1000) : 0} barColor="b" />
        <StatTile label="Transactions" value={kpis ? kpis.total_transactions.toLocaleString() : '--'}
          delta={kpis ? `${kpis.active_households} households` : ''} deltaColor="g"
          barPct={kpis ? Math.min(100, kpis.total_transactions / 10) : 0} barColor="g" />
        <StatTile label="Avg Basket" value={kpis ? `${kpis.avg_basket_thb.toFixed(0)} THB` : '--'}
          barPct={kpis ? Math.min(100, kpis.avg_basket_thb / 4) : 0} barColor="b" />
        <StatTile label="Churn Rate" value={kpis ? `${(kpis.churn_rate * 100).toFixed(1)}%` : '--'}
          deltaColor={kpis && kpis.churn_rate > 0.15 ? 'r' : 'g'}
          barPct={kpis ? kpis.churn_rate * 500 : 0}
          barColor={kpis && kpis.churn_rate > 0.15 ? 'r' : 'g'} />

        {/* Revenue Trend + Day of Week */}
        <ChartTile label="Daily Revenue Trend" span={7}>
          {revenue.length > 0 ? (
            <Line data={revChart} options={{...CHART_OPTS,
              scales: { x: { display: true, ticks: { maxTicksLimit: 10, font: { size: 9 } } },
                        y: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 } } } }
            }} />
          ) : <div className="empty-state"><div className="empty-text">No data</div></div>}
        </ChartTile>

        <ChartTile label="Revenue by Day of Week" span={5}>
          {dowData.length > 0 ? (
            <Bar data={dowChart} options={{...CHART_OPTS,
              scales: { y: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 } } },
                        x: { ticks: { font: { size: 10 } } } }
            }} />
          ) : <div className="empty-state"><div className="empty-text">No data</div></div>}
        </ChartTile>

        {/* Top SKUs + Lifecycle */}
        <ChartTile label="Top Products by Revenue" span={7}>
          {topSkus.length > 0 ? (
            <Bar data={skuChart} options={{...CHART_OPTS, indexAxis: 'y',
              scales: { x: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 9 } } },
                        y: { ticks: { font: { size: 10 } } } }
            }} />
          ) : <div className="empty-state"><div className="empty-text">No data</div></div>}
        </ChartTile>

        <ChartTile label="Customer Lifecycle" span={5}>
          {lcChart ? (
            <Doughnut data={lcChart} options={{
              responsive: true, maintainAspectRatio: false,
              plugins: { legend: { position: 'right', labels: { font: { size: 10 }, boxWidth: 12, padding: 8 } } },
              cutout: '55%',
            }} />
          ) : <div className="empty-state"><div className="empty-text">No data</div></div>}
        </ChartTile>

        {/* Insights */}
        <FindingTile label="Key Insights" span={12}
          text={kpis ? [
            `Village economy with ${kpis.active_households} households generated ${kpis.total_revenue.toLocaleString()} THB across ${kpis.total_transactions.toLocaleString()} transactions over ${kpis.days_simulated} days.`,
            topCustomer ? ` Top customer (${topCustomer.household_id}) spent ${topCustomer.total_spend?.toLocaleString()} THB in ${topCustomer.total_visits} visits.` : '',
            peakDay ? ` Peak day: ${peakDay.day_of_week} with ${peakDay.revenue?.toLocaleString()} THB revenue.` : '',
            totalStockoutLoss > 0 ? ` Stockout-related revenue loss: ${totalStockoutLoss.toLocaleString()} THB across ${stockouts.length} affected SKUs.` : '',
          ].join('') : 'No simulation data yet. Generate a challenge to get started.'}
          badge={kpis ? 'LIVE DATA' : 'NO DATA'} badgeClass={kpis ? 'green' : 'gray'}
        />

        {/* Stockout Impact Table */}
        {stockouts.length > 0 && (
          <FullWidthTile label="Stockout Impact" badge={`${stockouts.length} affected SKUs`} badgeClass="red">
            <table className="data-table">
              <thead>
                <tr><th>SKU</th><th>Stockout Events</th><th>Units Lost</th><th>Revenue Lost (THB)</th><th>Customers Affected</th></tr>
              </thead>
              <tbody>
                {stockouts.slice(0, 8).map(s => (
                  <tr key={s.sku_id}>
                    <td style={{fontWeight: 600}}>{s.sku_name}</td>
                    <td>{s.stockout_events}</td>
                    <td>{s.units_lost}</td>
                    <td style={{color: '#dc2626', fontWeight: 600}}>{s.revenue_lost?.toLocaleString()}</td>
                    <td>{s.customers_affected}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </FullWidthTile>
        )}

        {/* Top Customers */}
        <FullWidthTile label="Top Customers" badge={`${customers.length} total`} badgeClass="blue">
          <table className="data-table">
            <thead>
              <tr><th>Household</th><th>Size</th><th>Income</th><th>Zone</th><th>Visits</th><th>Total Spend</th><th>Avg Basket</th><th>Satisfaction</th></tr>
            </thead>
            <tbody>
              {customers.slice(0, 10).map(c => (
                <tr key={c.household_id}>
                  <td style={{fontWeight: 600}}>{c.household_id}</td>
                  <td>{c.household_size}</td>
                  <td><span className={`tile-badge ${c.income_bracket === 'high' ? 'green' : c.income_bracket === 'medium' ? 'blue' : 'gray'}`}>{c.income_bracket}</span></td>
                  <td>{c.location_zone}</td>
                  <td>{c.total_visits}</td>
                  <td style={{fontWeight: 600}}>{c.total_spend?.toLocaleString()} THB</td>
                  <td>{c.avg_basket?.toFixed(0)} THB</td>
                  <td>
                    <div className="stat-bar" style={{width: 60, display: 'inline-block'}}>
                      <div className={`stat-fill ${c.avg_satisfaction > 0.6 ? 'g' : c.avg_satisfaction > 0.3 ? 'y' : 'r'}`}
                           style={{width: `${c.avg_satisfaction * 100}%`}} />
                    </div>
                    <span style={{fontSize: 10, marginLeft: 6, color: '#888'}}>{(c.avg_satisfaction * 100).toFixed(0)}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </FullWidthTile>

        {/* Active Episodes */}
        <FullWidthTile label="Episodes" badge={`${episodes.length} total`} badgeClass="blue">
          {episodes.length > 0 ? (
            <div className="acts-grid">
              {episodes.map(ep => (
                <Link key={ep.episode_id} to="/challenges" style={{ textDecoration: 'none' }}>
                  <div className="act-card">
                    <div style={{fontSize: 10, letterSpacing: 2, color: '#1d4ed8', fontWeight: 700, textTransform: 'uppercase', marginBottom: 6}}>{ep.episode_id}</div>
                    <div className="ac-title">{ep.title || ep.episode_id.toUpperCase()}</div>
                    <div className="ac-desc">{ep.primary_business} | Tier {ep.tier} | {ep.challenge_type?.replace(/_/g, ' ')}</div>
                    <span className={`ep-status ${ep.status}`}>{ep.status}</span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
              No episodes. <Link to="/challenges" style={{ color: '#1d4ed8' }}>Create one</Link>
            </div>
          )}
        </FullWidthTile>
      </TileGrid>
    </div>
  )
}
