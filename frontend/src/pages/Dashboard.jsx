import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Line, Bar, Doughnut } from 'react-chartjs-2'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Filler, Legend } from 'chart.js'
import { api } from '../api'
import { TileGrid, StatTile, FindingTile, ChartTile, FullWidthTile } from '../components/TileGrid'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Filler, Legend)
const CO = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }

export default function Dashboard() {
  const { id } = useParams()
  const [ep, setEp] = useState(null)
  const [kpis, setKpis] = useState(null)
  const [revenue, setRevenue] = useState([])
  const [topSkus, setTopSkus] = useState([])
  const [dow, setDow] = useState([])
  const [lc, setLc] = useState(null)
  const [customers, setCustomers] = useState([])
  const [stockouts, setStockouts] = useState([])

  useEffect(() => {
    if (!id) return
    api.getEpisode(id).then(setEp).catch(() => {})
    api.getKPIs(id).then(setKpis).catch(() => setKpis(null))
    api.dailyRevenue(id).then(setRevenue).catch(() => setRevenue([]))
    api.topSkus(id, null, 10).then(setTopSkus).catch(() => setTopSkus([]))
    api.dayOfWeek(id).then(setDow).catch(() => setDow([]))
    api.lifecycleSummary(id).then(setLc).catch(() => setLc(null))
    api.customerSummary(id).then(setCustomers).catch(() => setCustomers([]))
    api.stockoutImpact(id).then(setStockouts).catch(() => setStockouts([]))
  }, [id])

  const fmt = n => n >= 1000 ? `${(n/1000).toFixed(1)}K` : String(Math.round(n))

  // Charts
  const revChart = { labels: revenue.map(r => `${r.day}`), datasets: [{
    data: revenue.map(r => r.revenue), borderColor: '#1d4ed8', backgroundColor: 'rgba(29,78,216,.06)',
    fill: true, tension: .3, pointRadius: 1.5 }] }
  const dowChart = { labels: dow.map(d => d.day_of_week?.slice(0,3).toUpperCase()),
    datasets: [{ data: dow.map(d => d.revenue), backgroundColor: dow.map((d,i) => i>=4 ? '#1d4ed8' : '#bfdbfe'), borderRadius: 4 }] }
  const lcColors = { retained:'#22c55e', at_risk:'#f59e0b', churned:'#ef4444', aware:'#60a5fa', unaware:'#d1d5db', new_acquisition:'#34d399', winback_candidate:'#a78bfa', dormant:'#9ca3af' }
  const lcChart = lc?.states ? { labels: lc.states.map(s => s.lifecycle_state.replace(/_/g,' ')),
    datasets: [{ data: lc.states.map(s => s.count), backgroundColor: lc.states.map(s => lcColors[s.lifecycle_state]||'#d1d5db'), borderWidth: 0 }] } : null
  const skuChart = { labels: topSkus.slice(0,8).map(s => s.sku_name?.length>20 ? s.sku_name.slice(0,20)+'...' : s.sku_name),
    datasets: [{ data: topSkus.slice(0,8).map(s => s.revenue), backgroundColor: '#1d4ed8', borderRadius: 4 }] }

  const topCust = customers[0]
  const soLoss = stockouts.reduce((s,r) => s+(r.revenue_lost||0), 0)
  const peak = dow.reduce((m,d) => d.revenue>(m?.revenue||0)?d:m, null)

  return <div>
    <div className="page-header">
      <div>
        <h1 className="page-title">{ep ? `${id.toUpperCase()} — ${ep.title || 'Dashboard'}` : 'Dashboard'}</h1>
        <p className="page-subtitle">{ep ? `${ep.primary_business} | Tier ${ep.tier} | ${ep.challenge_type?.replace(/_/g,' ')}` : ''}</p>
      </div>
      <div style={{display:'flex',gap:8}}>
        <Link to={`/challenges/${id}`} className="btn btn-secondary btn-sm">Manage</Link>
        <Link to="/" className="btn btn-secondary btn-sm">All Challenges</Link>
      </div>
    </div>

    <TileGrid>
      <StatTile label="Total Revenue" value={kpis?`${fmt(kpis.total_revenue)} THB`:'--'} delta={kpis?`${kpis.days_simulated}d`:''} deltaColor="g" barPct={kpis?Math.min(100,kpis.total_revenue/20000):0} barColor="b" />
      <StatTile label="Transactions" value={kpis?kpis.total_transactions.toLocaleString():'--'} delta={kpis?`${kpis.active_households} HH`:''} deltaColor="g" barPct={kpis?Math.min(100,kpis.total_transactions/100):0} barColor="g" />
      <StatTile label="Avg Basket" value={kpis?`${kpis.avg_basket_thb.toFixed(0)} THB`:'--'} barPct={kpis?Math.min(100,kpis.avg_basket_thb/5):0} barColor="b" />
      <StatTile label="Churn Rate" value={kpis?`${(kpis.churn_rate*100).toFixed(1)}%`:'--'} barPct={kpis?kpis.churn_rate*500:0} barColor={kpis&&kpis.churn_rate>.15?'r':'g'} />

      <ChartTile label="Revenue Trend" span={7}>
        {revenue.length>0 ? <Line data={revChart} options={{...CO, scales:{x:{ticks:{maxTicksLimit:12,font:{size:9}}}, y:{grid:{color:'#f0f0f0'}}}}} /> : <p style={{color:'#999',textAlign:'center',pt:60}}>No data</p>}
      </ChartTile>
      <ChartTile label="Day of Week" span={5}>
        {dow.length>0 ? <Bar data={dowChart} options={{...CO, scales:{y:{grid:{color:'#f0f0f0'}}}}} /> : <p style={{color:'#999',textAlign:'center',pt:60}}>No data</p>}
      </ChartTile>

      <ChartTile label="Top Products" span={7}>
        {topSkus.length>0 ? <Bar data={skuChart} options={{...CO, indexAxis:'y', scales:{x:{grid:{color:'#f0f0f0'}},y:{ticks:{font:{size:10}}}}}} /> : <p style={{color:'#999',textAlign:'center',pt:60}}>No data</p>}
      </ChartTile>
      <ChartTile label="Customer Lifecycle" span={5}>
        {lcChart ? <Doughnut data={lcChart} options={{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{size:10},boxWidth:12}}},cutout:'55%'}} /> : <p style={{color:'#999',textAlign:'center',pt:60}}>No data</p>}
      </ChartTile>

      <FindingTile label="Key Insights" span={12}
        text={kpis ? [
          `${kpis.active_households} households, ${kpis.total_revenue.toLocaleString()} THB total revenue, ${kpis.total_transactions.toLocaleString()} transactions over ${kpis.days_simulated} days.`,
          topCust?` Top customer: ${topCust.household_id} (${topCust.total_spend?.toLocaleString()} THB, ${topCust.total_visits} visits).`:'',
          peak?` Peak day: ${peak.day_of_week}.`:'',
          soLoss>0?` Stockout loss: ${soLoss.toLocaleString()} THB.`:'',
        ].join('') : 'No data yet.'}
        badge={kpis?'LIVE':'NO DATA'} badgeClass={kpis?'green':'gray'} />

      {stockouts.length>0 && <FullWidthTile label="Stockout Impact" badge={`${stockouts.length} SKUs`} badgeClass="red">
        <table className="data-table"><thead><tr><th>SKU</th><th>Events</th><th>Units Lost</th><th>Revenue Lost</th><th>Affected</th></tr></thead>
          <tbody>{stockouts.slice(0,8).map(s=><tr key={s.sku_id}><td style={{fontWeight:600}}>{s.sku_name}</td><td>{s.stockout_events}</td><td>{s.units_lost}</td><td style={{color:'#dc2626',fontWeight:600}}>{s.revenue_lost?.toLocaleString()}</td><td>{s.customers_affected}</td></tr>)}</tbody></table>
      </FullWidthTile>}

      <FullWidthTile label="Top Customers" badge={`${customers.length}`} badgeClass="blue">
        <table className="data-table"><thead><tr><th>Household</th><th>Size</th><th>Income</th><th>Visits</th><th>Spend</th><th>Avg Basket</th><th>Satisfaction</th></tr></thead>
          <tbody>{customers.slice(0,10).map(c=><tr key={c.household_id}><td style={{fontWeight:600}}>{c.household_id}</td><td>{c.household_size}</td>
            <td><span className={`tile-badge ${c.income_bracket==='high'?'green':c.income_bracket==='medium'?'blue':'gray'}`}>{c.income_bracket}</span></td>
            <td>{c.total_visits}</td><td style={{fontWeight:600}}>{c.total_spend?.toLocaleString()}</td><td>{c.avg_basket?.toFixed(0)}</td>
            <td><div className="stat-bar" style={{width:60,display:'inline-block'}}><div className={`stat-fill ${c.avg_satisfaction>.6?'g':c.avg_satisfaction>.3?'y':'r'}`} style={{width:`${c.avg_satisfaction*100}%`}}/></div> <span style={{fontSize:10,color:'#888'}}>{(c.avg_satisfaction*100).toFixed(0)}%</span></td></tr>)}</tbody></table>
      </FullWidthTile>
    </TileGrid>
  </div>
}
