import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { Bell, ChevronRight, UserRound } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'

const TITLES = [
  ['/app/dashboard', 'Dashboard'],
  ['/app/products', 'Products'],
  ['/app/invoices', 'Invoices'],
  ['/app/sales', 'Sales'],
  ['/app/history', 'History'],
  ['/app/settings', 'Settings'],
]

export default function Navbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => { setOpen(false) }, [pathname])
  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const title = TITLES.find(([p]) => pathname.startsWith(p))?.[1] || 'StockLens'
  const name = user?.name || user?.full_name || user?.email || 'Account'
  const initials = name.split(/\s+/).map((x) => x[0]).join('').slice(0, 2).toUpperCase()

  return (
    <header className="topbar">
      <span>{title}</span>
      <div ref={ref}>
        <button className="icon-button" aria-label="Notifications"><Bell size={20} /><i /></button>
        <button className="account-button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          <span className="avatar">{initials}</span>
          <span className="user"><strong>{name}</strong><small>{user?.email}</small></span>
          <ChevronRight size={15} />
        </button>
        {open && (
          <div className="account-menu" role="menu">
            <div><strong>{name}</strong><small>{user?.email}</small></div>
            <button role="menuitem" onClick={() => navigate('/app/settings')}><UserRound />Account settings</button>
          </div>
        )}
      </div>
    </header>
  )
}
