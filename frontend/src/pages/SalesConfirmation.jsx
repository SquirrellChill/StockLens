import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { CheckCircle2 } from 'lucide-react'
import Button from '../components/Button'
import { EmptyState } from '../components/Feedback'
import { salesService } from '../services/salesService'
import { formatCurrency } from '../utils/formatCurrency'

export default function SalesConfirmation() {
  const navigate = useNavigate()
  const [items] = useState(() => salesService.getDraft())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(null)

  useEffect(() => { if (!items.length && !done) navigate('/app/sales', { replace: true }) }, [items, done, navigate])

  const confirm = async () => {
    setBusy(true)
    setError('')
    try {
      setDone(await salesService.confirm(items))
    } catch (e) {
      setError(e.message || 'Could not record these sales. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <section className="flow-card">
        <EmptyState
          icon={CheckCircle2}
          title="Sales recorded"
          text={`${formatCurrency(done.total)} across ${done.items.length} product${done.items.length === 1 ? '' : 's'}. Stock has been updated.`}
          action={<Button onClick={() => navigate('/app/dashboard')}>Back to dashboard</Button>}
        />
      </section>
    )
  }

  const total = items.reduce((s, i) => s + i.quantity * i.unit_price, 0)

  return (
    <>
      <div className="title-row"><div><h1>Confirm today’s sales</h1><p>Stock will be reduced by these quantities.</p></div></div>
      <section className="panel" style={{ maxWidth: 720 }}>
        {items.map((i) => (
          <div className="draft-row" key={i.product_id}><div><strong>{i.name}</strong><small>{formatCurrency(i.unit_price)} each</small></div><span>× {i.quantity}</span><b>{formatCurrency(i.quantity * i.unit_price)}</b></div>
        ))}
        <div className="draft-total"><span>Total</span><span>{formatCurrency(total)}</span></div>
        {error && <div className="form-error" role="alert" style={{ margin: '0 20px 14px' }}>{error}</div>}
        <div className="flow-actions" style={{ padding: '0 20px 20px' }}>
          <Button kind="secondary" onClick={() => navigate('/app/sales')}>Back</Button>
          <Button disabled={busy} onClick={confirm}>{busy ? 'Saving…' : 'Confirm sales'}</Button>
        </div>
      </section>
    </>
  )
}
