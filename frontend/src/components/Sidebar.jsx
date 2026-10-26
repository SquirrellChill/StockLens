import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { Boxes, History, Home, LayoutDashboard, MoreHorizontal, ReceiptText, Settings, ShoppingCart } from 'lucide-react'
import Logo from './Logo'
import { useAuth } from '../auth/AuthContext'

export const NAV = [
  { to: '/app/dashboard', label: 'Dashboard', short: 'Home', icon: LayoutDashboard, mobileIcon: Home },
  { to: '/app/products', label: 'Products', short: 'Products', icon: Boxes },
  { to: '/app/invoices', label: 'Invoices', short: 'Invoices', icon: ReceiptText },
  { to: '/app/sales', label: 'Sales', short: 'Sales', icon: ShoppingCart },
  { to: '/app/history', label: 'History', short: 'History', icon: History },
]

const isActive = (pathname, to) => pathname === to || pathname.startsWith(`${to}/`)

export default function Sidebar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [more, setMore] = useState(false)
  const go = (to) => { navigate(to); setMore(false) }

  const name = user?.name || user?.full_name || user?.email || 'Account'
  const initials = name.split(/\s+/).map((x) => x[0]).join('').slice(0, 2).toUpperCase()
  const bottom = NAV.slice(0, 4)

  return (
    <>
      <aside className="sidebar">
        <Logo />
        <nav>
          {NAV.map(({ to, label, icon: Icon }) => (
            <button key={to} className={isActive(pathname, to) ? 'active' : ''} onClick={() => go(to)}><Icon size={20} />{label}</button>
          ))}
        </nav>
        <button className={isActive(pathname, '/app/settings') ? 'side-settings active' : 'side-settings'} onClick={() => go('/app/settings')}><Settings size={20} />Settings</button>
      </aside>

      <header className="mobile-header">
        <Logo />
        <button className="mobile-account" aria-label="Account settings" onClick={() => go('/app/settings')}>{initials}</button>
      </header>

      <nav className="bottom-nav">
        {bottom.map(({ to, short, icon, mobileIcon }) => {
          const Icon = mobileIcon || icon
          return <button key={to} className={isActive(pathname, to) ? 'active' : ''} onClick={() => go(to)}><Icon size={21} /><span>{short}</span></button>
        })}
        <button className={more || isActive(pathname, '/app/history') || isActive(pathname, '/app/settings') ? 'active' : ''} onClick={() => setMore(!more)}><MoreHorizontal size={22} /><span>More</span></button>
      </nav>
      {more && (
        <div className="more-menu">
          <button onClick={() => go('/app/history')}><History />History</button>
          <button onClick={() => go('/app/settings')}><Settings />Settings</button>
        </div>
      )}
    </>
  )
}
