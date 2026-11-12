import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { ImagePlus } from 'lucide-react'
import Button from '../components/Button'
import InvoiceDraftCard from '../components/InvoiceDraftCard'
import { useInvoiceDrafts } from '../hooks/useInvoiceDrafts'
import { USE_MOCK } from '../services/api'
import { draftLines, draftProblems, draftTotal, invoiceService } from '../services/invoiceService'
import { formatCurrency } from '../utils/formatCurrency'

export default function InvoiceReview() {
  const navigate = useNavigate()
  const drafts = useInvoiceDrafts()
  const [saving, setSaving] = useState(false)
  const [summary, setSummary] = useState('')
  const [errors, setErrors] = useState([])
  const moreRef = useRef(null)
  const pending = drafts.filter((d) => d.status !== 'saved')

  useEffect(() => { document.title = 'Review invoices · StockLens' }, [])

  if (!drafts.length) return <Navigate to="/app/invoices/upload" replace />

  const ready = pending.filter((d) => d.status === 'ready')
  const reading = pending.filter((d) => d.status === 'reading').length
  const failed = pending.filter((d) => d.status === 'error').length
  const lineCount = ready.reduce((s, d) => s + draftLines(d).length, 0)
  const total = ready.reduce((s, d) => s + draftTotal(d), 0)
  const problems = ready.reduce((s, d) => s + draftProblems(d), 0)

  const confirm = async () => {
    setSaving(true)
    setSummary('')
    const { saved, failed: bad } = await invoiceService.confirmAll()
    setSaving(false)
    if (!bad) { navigate('/app/invoices'); return }
    setSummary(`${saved} invoice${saved === 1 ? '' : 's'} saved. ${bad} could not be saved: see the message on ${bad === 1 ? 'it' : 'each one'} below, fix it and confirm again.`)
  }

  const canConfirm = ready.length > 0 && reading === 0 && !saving && problems === 0

  return (
    <>
      <div className="title-row">
        <div><h1>Review {pending.length > 1 ? 'invoices' : 'invoice'}</h1><p>Check every item. Stock is only updated when you confirm.</p></div>
        <Button kind="secondary" icon={ImagePlus} onClick={() => moreRef.current?.click()}>Add more invoices</Button>
        <input ref={moreRef} type="file" accept="image/*" multiple hidden onChange={(e) => { setErrors(invoiceService.addFiles(e.target.files)); e.target.value = '' }} />
      </div>
      {USE_MOCK && <div className="mode-banner">Automatic invoice reading needs the backend. Enter the items from each invoice below.</div>}
      {errors.length > 0 && <div className="form-error" role="alert">{errors.map((m, i) => <div key={i}>{m}</div>)}</div>}
      {summary && <div className="notice warning" role="alert"><div><strong>Some invoices need attention</strong><p>{summary}</p></div></div>}

      <section className="draft-list">
        {drafts.map((d, i) => <InvoiceDraftCard key={d.id} draft={d} index={i} total={drafts.length} />)}
      </section>

      <section className="flow-card confirm-bar">
        <div className="confirm-summary">
          <strong>{ready.length} invoice{ready.length === 1 ? '' : 's'} · {lineCount} item{lineCount === 1 ? '' : 's'} · {formatCurrency(total)}</strong>
          <small>
            {reading > 0 ? `Still reading ${reading}… you can confirm once they finish.`
              : failed > 0 ? `${failed} invoice${failed === 1 ? '' : 's'} couldn’t be read. Retry or remove ${failed === 1 ? 'it' : 'them'}; the rest can still be saved.`
              : problems > 0 ? `${problems} row${problems === 1 ? '' : 's'} still need fixing.`
              : 'Existing products get more stock; new items are added to your inventory.'}
          </small>
        </div>
        <div className="flow-actions" style={{ marginTop: 0 }}>
          <Button kind="secondary" onClick={() => navigate('/app/invoices/upload')}>Back</Button>
          <Button disabled={!canConfirm} onClick={confirm}>{saving ? 'Saving…' : ready.length > 1 ? `Confirm all ${ready.length} & add stock` : 'Confirm & add stock'}</Button>
        </div>
      </section>
    </>
  )
}
