import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { AlertTriangle, Bell, CalendarClock, PackageX } from 'lucide-react'
import { isExpiringSoon, isLowStock, productService } from '../services/productService'

const DAY = 864e5

function buildAlerts(products) {
  const alerts = []
  for (const p of products) {
    const qty = Number(p.quantity)
    if (qty <= 0) alerts.push({ id: `out-${p.id}`, kind: 'danger', icon: PackageX, rank: 0, title: `${p.name} is out of stock`, text: 'Restock to keep selling.' })
    else if (isLowStock(p)) alerts.push({ id: `low-${p.id}`, kind: 'warn', icon: AlertTriangle, rank: 2, title: `${p.name} is running low`, text: `Only ${qty} left.` })
    if (isExpiringSoon(p)) {
      const days = Math.ceil((new Date(p.expiration_date).getTime() - Date.now()) / DAY)
      alerts.push(days < 0
        ? { id: `exp-${p.id}`, kind: 'danger', icon: CalendarClock, rank: 1, title: `${p.name} has expired`, text: `Expired ${-days} day${days === -1 ? '' : 's'} ago.` }
        : { id: `soon-${p.id}`, kind: 'warn', icon: CalendarClock, rank: 3, title: `${p.name} expires soon`, text: days <= 0 ? 'Expires today.' : `Expires in ${days} day${days === 1 ? '' : 's'}.` })
    }
  }
  return alerts.sort((a, b) => a.rank - b.rank)
}

export default function NotificationBell() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [alerts, setAlerts] = useState([])
  const [open, setOpen] = useState(false)
  const [failed, setFailed] = useState(false)
  const ref = useRef(null)

  const load = useCallback(() => {
    productService.list()
      .then((list) => { setAlerts(buildAlerts(list)); setFailed(false) })
      .catch(() => setFailed(true))
  }, [])

  // Refresh on every navigation so counts follow sales / invoices / edits.
  useEffect(() => { load(); setOpen(false) }, [pathname, load])
  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    const esc = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc) }
  }, [])

  const toggle = () => { if (!open) load(); setOpen(!open) }

  return (
    <div className="bell" ref={ref}>
      <button className="icon-button" aria-label={alerts.length ? `Notifications, ${alerts.length} new` : 'Notifications'} aria-haspopup="true" aria-expanded={open} onClick={toggle}>
        <Bell size={20} />
        {alerts.length > 0 && <i className="bell-badge">{alerts.length > 9 ? '9+' : alerts.length}</i>}
      </button>
      {open && (
        <div className="bell-menu" role="region" aria-label="Notifications">
          <div className="bell-head"><strong>Notifications</strong>{alerts.length > 0 && <span>{alerts.length}</span>}</div>
          {failed && <p className="bell-empty">Couldn’t load notifications.</p>}
          {!failed && !alerts.length && <p className="bell-empty">You’re all caught up. Stock levels and expiry dates look good.</p>}
          <div className="bell-list">
            {alerts.map(({ id, kind, icon: Icon, title, text }) => (
              <button key={id} className={`bell-item ${kind}`} onClick={() => navigate('/app/products')}>
                <span><Icon size={16} /></span>
                <div><strong>{title}</strong><small>{text}</small></div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
