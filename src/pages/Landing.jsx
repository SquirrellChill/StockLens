import { Link, Navigate } from 'react-router'
import { BarChart3, Boxes, FileScan, Mic, ShieldCheck } from 'lucide-react'
import Logo from '../components/Logo'
import { useAuth } from '../auth/AuthContext'

const FEATURES = [
  [Boxes, 'Inventory management', 'Know what is in stock and what needs attention.'],
  [FileScan, 'Invoice scanning', 'Turn supplier invoices into stock updates.'],
  [Mic, 'Voice-based sales', 'Record daily sales naturally with your voice.'],
  [BarChart3, 'Clear history', 'Understand sales and spending at a glance.'],
]

export default function Landing() {
  const { user, checking } = useAuth()
  if (!checking && user) return <Navigate to="/app/dashboard" replace />

  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo />
        <div>
          <Link className="button secondary" to="/login">Log in</Link>
          <Link className="button primary" to="/signup">Get started</Link>
        </div>
      </header>
      <main className="landing-main">
        <section className="hero">
          <div className="hero-copy">
            <span className="eyebrow"><ShieldCheck size={15} /> Built for independent shop owners</span>
            <h1>Manage Your Stock <em>Smarter.</em></h1>
            <p>StockLens brings inventory, supplier invoices, voice-based sales, and stock insights into one simple workspace—so you can spend less time counting and more time serving customers.</p>
            <div className="hero-actions">
              <Link className="button primary" to="/signup">Get started</Link>
              <Link className="button secondary" to="/login">Log in</Link>
            </div>
            <small>No spreadsheets. No complicated setup.</small>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="visual-top"><span>Shop overview</span><i>Today</i></div>
            <div className="visual-cards">
              <b><Boxes /> <small>Total products</small><strong>248</strong></b>
              <b><BarChart3 /> <small>Today’s sales</small><strong>$1,284</strong></b>
            </div>
            <div className="visual-list">
              <span><i>1</i><b>Low stock items</b><small>3 products</small></span>
              <span><i>2</i><b>Invoice processed</b><small>Just now</small></span>
              <span><i>3</i><b>Sales recorded</b><small>12 items</small></span>
            </div>
          </div>
        </section>
        <section className="features">
          <div className="section-title"><span>EVERYTHING YOU NEED</span><h2>Simple tools for a smoother day</h2><p>Stay on top of your shop without learning complicated software.</p></div>
          <div className="feature-grid">
            {FEATURES.map(([Icon, title, text]) => <article key={title}><i><Icon /></i><h3>{title}</h3><p>{text}</p></article>)}
          </div>
        </section>
      </main>
      <footer className="landing-footer"><Logo /><span>Simple inventory, clearer decisions.</span><small>© {new Date().getFullYear()} StockLens</small></footer>
    </div>
  )
}
