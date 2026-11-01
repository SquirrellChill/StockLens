import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { Plus, Trash2 } from 'lucide-react'
import Button from '../components/Button'
import { USE_MOCK } from '../services/api'
import { invoiceService } from '../services/invoiceService'
import { formatCurrency } from '../utils/formatCurrency'

const blank = () => ({ name: '', quantity: 1, unit_price: '' })

export default function InvoiceReview() {
  const navigate = useNavigate()
  const staged = invoiceService.getStaged()
  const [supplier, setSupplier] = useState(staged?.supplier || '')
  const [number, setNumber] = useState(staged?.invoice_number || '')
  const [items, setItems] = useState(staged?.items?.length ? staged.items : [blank()])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { invoiceService.updateStaged({ supplier, invoice_number: number, items }) }, [supplier, number, items])

  if (!staged) return <Navigate to="/app/invoices/upload" replace />

  const setItem = (i, key, value) => setItems(items.map((it, x) => (x === i ? { ...it, [key]: value } : it)))
  const total = items.reduce((s, i) => s + (Number(i.quantity) || 0) * (Number(i.unit_price) || 0), 0)

  const confirm = async () => {
    setSaving(true)
    setError('')
    try {
      await invoiceService.confirm({ supplier, invoice_number: number, items })
      navigate('/app/invoices')
    } catch (e) {
      setError(e.message || 'Could not save this invoice. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="title-row"><div><h1>Review invoice</h1><p>Check every item. Stock is only updated when you confirm.</p></div></div>
      {USE_MOCK && <div className="mode-banner">Automatic invoice reading needs the backend. Enter the items from your invoice below.</div>}
      <section className="flow-card">
        <div className="steps"><b>1<span>Upload</span></b><i /><b className="active">2<span>Review</span></b><i /><b>3<span>Confirm</span></b></div>
        <div className="field-row">
          <label>Supplier<input value={supplier} onChange={(e) => setSupplier(e.target.value)} placeholder="e.g. Fresh Foods Co." /></label>
          <label>Invoice number<input value={number} onChange={(e) => setNumber(e.target.value)} placeholder="e.g. INV-1042" /></label>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="review-table">
            <thead><tr><th>Item</th><th style={{ width: 100 }}>Qty</th><th style={{ width: 130 }}>Unit price</th><th style={{ width: 44 }} /></tr></thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i}>
                  <td><input aria-label="Item name" value={it.name} onChange={(e) => setItem(i, 'name', e.target.value)} placeholder="Item name" /></td>
                  <td><input aria-label="Quantity" type="number" min="1" value={it.quantity} onChange={(e) => setItem(i, 'quantity', e.target.value)} /></td>
                  <td><input aria-label="Unit price" type="number" min="0" step=".01" value={it.unit_price} onChange={(e) => setItem(i, 'unit_price', e.target.value)} placeholder="0.00" /></td>
                  <td><button type="button" aria-label="Remove item" className="icon-button" onClick={() => setItems(items.filter((_, x) => x !== i))}><Trash2 size={16} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button type="button" className="text-button" style={{ marginTop: 12 }} onClick={() => setItems([...items, blank()])}><Plus size={16} /> Add item</button>
        <div className="draft-total"><span>Total</span><span>{formatCurrency(total)}</span></div>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="flow-actions">
          <Button kind="secondary" onClick={() => navigate('/app/invoices/upload')}>Back</Button>
          <Button disabled={saving} onClick={confirm}>{saving ? 'Saving…' : 'Confirm & add stock'}</Button>
        </div>
      </section>
    </>
  )
}
