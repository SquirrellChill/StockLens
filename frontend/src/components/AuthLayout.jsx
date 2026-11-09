import { Link } from 'react-router'
import Logo from './Logo'

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="auth-layout">
      <div className="auth-aside">
        <Link to="/"><Logo /></Link>
        <div>
          <span className="eyebrow">STOCKLENS</span>
          <h2>Your shop, clearly managed.</h2>
          <p>Track products, scan invoices, and record sales without the paperwork.</p>
        </div>
        <small>Built for small shops with big ambitions.</small>
      </div>
      <main className="auth-main">
        <Link className="auth-brand-mobile" to="/"><Logo /></Link>
        <div className="auth-card">
          <div className="auth-heading"><h1>{title}</h1><p>{subtitle}</p></div>
          {children}
        </div>
      </main>
    </div>
  )
}
