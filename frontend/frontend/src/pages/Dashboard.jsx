import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { AlertTriangle, CalendarDays, ChevronRight, CircleDollarSign, ClipboardList, History, Mic, Package, ReceiptText } from 'lucide-react'
import DashboardCard from '../components/DashboardCard'
import { EmptyState, ErrorNotice, Loader } from '../components/Feedback'
import { useAuth } from '../auth/AuthContext'
import { dashboardService } from '../services/dashboardService'
import { formatCurrency } from '../utils/formatCurrency'

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    dashboardService.summary().then(setSummary).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [])
  useEffect(load, [load])

  const first = (user?.name || user?.full_name || '').split(' ')[0]

  return (
    <>
      <section className="welcome-row">
        <div><h1>{greeting()}{first ? `, ${first}` : ''}!</h1><p>Here’s your shop overview.</p></div>
        <div className="date-pill"><CalendarDays size={17} /> {new Intl.DateTimeFormat('en', { weekday: 'short', month: 'long', day: 'numeric' }).format(new Date())}</div>
      </section>

      {error && <ErrorNotice title="Dashboard data is unavailable" message={error} onRetry={load} />}

      <div className="stats-grid">
        <DashboardCard icon={Package} label="Total products" value={loading ? '…' : summary?.total_products ?? '—'} note="Products in inventory" />
        <DashboardCard icon={CircleDollarSign} label="Today’s sales" value={loading ? '…' : summary?.today_sales != null ? formatCurrency(summary.today_sales) : '—'} note="Confirmed sales today" tone="blue" />
        <DashboardCard icon={AlertTriangle} label="Low stock" value={loading ? '…' : summary?.low_stock ?? '—'} note="Items need attention" tone="amber" />
      </div>

      <div className="quick-grid">
        <button className="quick-card" onClick={() => navigate('/app/invoices/upload')}><span className="quick-icon"><ReceiptText /></span><span><strong>Scan Invoice</strong><small>Add stock from a supplier invoice</small></span><ChevronRight /></button>
        <button className="quick-card" onClick={() => navigate('/app/sales/voice')}><span className="quick-icon dark"><Mic /></span><span><strong>Record Sale</strong><small>Update stock using your voice</small></span><ChevronRight /></button>
      </div>

      <div className="two-column">
        <section className="panel">
          <div className="panel-head"><div><h2>Low stock items</h2><p>Products that need restocking</p></div><button onClick={() => navigate('/app/products')}>View all <ChevronRight size={15} /></button></div>
          {loading ? <Loader /> : summary?.low_stock_items?.length
            ? summary.low_stock_items.map((p) => (
              <div className="list-row" key={p.id}><div className="product-avatar">{p.name?.[0]}</div><div><strong>{p.name}</strong><small>{p.quantity} remaining</small></div><span className="status low">Low stock</span></div>
            ))
            : <EmptyState icon={Package} title="Nothing running low" text="Items at or below 5 units will appear here." />}
        </section>
        <section className="panel">
          <div className="panel-head"><div><h2>Recent activity</h2><p>Latest invoices and sales</p></div><button onClick={() => navigate('/app/history')}>View all <ChevronRight size={15} /></button></div>
          {loading ? <Loader /> : summary?.recent_activity?.length
            ? summary.recent_activity.map((a, i) => (
              <div className="list-row" key={i}><div className="activity-icon"><ClipboardList size={18} /></div><div><strong>{a.title}</strong><small>{a.date}</small></div><b>{a.amount}</b></div>
            ))
            : <EmptyState icon={History} title="No recent activity" text="Confirmed invoices and sales will show up here." />}
        </section>
      </div>
    </>
  )
}
