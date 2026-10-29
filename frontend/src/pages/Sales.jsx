import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Mic, Plus, ShoppingCart, Trash2 } from 'lucide-react'
import Button from '../components/Button'
import { EmptyState } from '../components/Feedback'
import { productService } from '../services/productService'
import { salesService } from '../services/salesService'
import { formatCurrency } from '../utils/formatCurrency'

/** Manual sale entry + today's draft. Stock is untouched until confirmation. */
export default function Sales() {
  const navigate = useNavigate()
  const [products, setProducts] = useState([])
  const [draft, setDraft] = useState(() => salesService.getDraft())
  const [query, setQuery] = useState('')
  const [qty, setQty] = useState(1)
  const [error, setError] = useState('')

  useEffect(() => { productService.list().then(setProducts).catch((e) => setError(e.message)) }, [])

  const update = (next) => { salesService.saveDraft(next); setDraft(next) }

  const add = (e) => {
    e.preventDefault()
    setError('')
    const q = query.trim().toLowerCase()
    const product = products.find((p) => [p.name, ...(p.alternative_names || [])].some((n) => n.toLowerCase() === q))
      || products.find((p) => [p.name, ...(p.alternative_names || [])].some((n) => n.toLowerCase().includes(q)) && q)
    if (!product) return setError('We couldn’t find that product. Check the name or add it to your products first.')
    setDraft(salesService.addToDraft(product, qty))
    setQuery('')
    setQty(1)
  }

  const total = draft.reduce((s, i) => s + i.quantity * i.unit_price, 0)

  return (
    <>
      <div className="title-row">
        <div><h1>Record today’s sales</h1><p>Add items by hand or by voice, then review before updating stock.</p></div>
        <Button kind="secondary" icon={Mic} onClick={() => navigate('/app/sales/voice')}>Use voice</Button>
      </div>
      <div className="sale-grid">
        <section className="flow-card" style={{ margin: 0, width: '100%' }}>
          <h2 style={{ marginBottom: 14 }}>Add manually</h2>
          {error && <div className="form-error" role="alert">{error}</div>}
          <form className="manual-sale" onSubmit={add}>
            <label><span>Product</span><input list="product-names" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search product" /></label>
            <datalist id="product-names">{products.map((p) => <option key={p.id} value={p.name} />)}</datalist>
            <label><span>Quantity</span><input type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} /></label>
            <Button type="submit" icon={Plus}>Add</Button>
          </form>
        </section>
        <section className="panel">
          <div className="panel-head"><div><h2>Today’s draft sales</h2><p>Stock stays unchanged until confirmation.</p></div><span className="count">{draft.length} item{draft.length === 1 ? '' : 's'}</span></div>
          {draft.length ? (
            <>
              {draft.map((item, i) => (
                <div className="draft-row" key={item.product_id}>
                  <div><strong>{item.name}</strong><small>{formatCurrency(item.unit_price)} each</small></div>
                  <input type="number" min="1" aria-label={`Quantity of ${item.name}`} value={item.quantity} onChange={(e) => update(draft.map((d, x) => (x === i ? { ...d, quantity: Math.max(1, parseInt(e.target.value, 10) || 1) } : d)))} />
                  <button type="button" aria-label={`Remove ${item.name}`} onClick={() => update(draft.filter((_, x) => x !== i))}><Trash2 size={17} /></button>
                </div>
              ))}
              <div className="draft-total"><span>Total</span><span>{formatCurrency(total)}</span></div>
            </>
          ) : <EmptyState icon={ShoppingCart} title="No sales added yet" text="Use your voice or add a product manually." />}
          <Button className="wide" disabled={!draft.length} onClick={() => navigate('/app/sales/confirm')}>Review daily sales</Button>
        </section>
      </div>
    </>
  )
}
