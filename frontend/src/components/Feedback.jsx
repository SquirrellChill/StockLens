import { AlertTriangle, LoaderCircle, Package } from 'lucide-react'

export function Loader({ text = 'Loading…' }) {
  return <div className="loader"><LoaderCircle className="spin" size={22} /> {text}</div>
}

export function EmptyState({ icon: Icon = Package, title, text, action }) {
  return (
    <div className="empty">
      <span className="empty-icon"><Icon size={23} /></span>
      <strong>{title}</strong>
      <p>{text}</p>
      {action}
    </div>
  )
}

export function ErrorNotice({ title, message, onRetry }) {
  return (
    <div className="notice warning" role="alert">
      <AlertTriangle size={19} />
      <div><strong>{title}</strong><p>{message}</p></div>
      {onRetry && <button type="button" onClick={onRetry}>Try again</button>}
    </div>
  )
}
