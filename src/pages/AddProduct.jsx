import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { Plus, X } from 'lucide-react'
import Button from '../components/Button'
import { ErrorNotice, Loader } from '../components/Feedback'
import { productService } from '../services/productService'
import { validateProduct } from '../utils/validation'

const EMPTY = { name: '', quantity: '', unit_price: '', expiration_date: '', alternative_names: [''] }

/** Handles both /app/products/new and /app/products/:id/edit */
export default function AddProduct() {
  const { id } = useParams()
  const navigate = useNavigate()
  const editing = !!id
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(editing)
  const [loadError, setLoadError] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!editing) return
    productService.get(id)
      .then((p) => setForm({ ...p, alternative_names: p.alternative_names?.length ? p.alternative_names : [''] }))
      .catch((e) => setLoadError(e.message))
      .finally(() => setLoading(false))
  }, [id, editing])

  const change = (key, value) => setForm((f) => ({ ...f, [key]: value }))
  const setAlt = (i, value) => change('alternative_names', form.alternative_names.map((n, x) => (x === i ? value : n)))

  const submit = async (e) => {
    e.preventDefault()
    const problem = validateProduct(form)
    if (problem) return setError(problem)
    setSaving(true)
    setError('')
    try {
      if (editing) await productService.update(id, form)
      else await productService.create(form)
      navigate('/app/products')
    } catch (err) {
      setError(err.message || 'Could not save your changes. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Loader />
  if (loadError) return <ErrorNotice title="Unable to load product" message={loadError} />

  return (
    <>
      <div className="title-row"><div><h1>{editing ? 'Edit product' : 'Add product'}</h1><p>{editing ? 'Update product details and stock.' : 'Add a new item to your inventory.'}</p></div></div>
      <form className="modal inline-modal" onSubmit={submit} noValidate>
        {error && <div className="form-error" role="alert">{error}</div>}
        <label><span>Product name *</span><input name="name" value={form.name} onChange={(e) => change('name', e.target.value)} placeholder="e.g. Coca-Cola 500ml" /></label>
        <div className="form-grid">
          <label><span>Quantity *</span><input name="quantity" type="number" min="0" value={form.quantity} onChange={(e) => change('quantity', e.target.value)} placeholder="0" /></label>
          <label><span>Unit price *</span><div className="money-input"><i>$</i><input name="unit_price" type="number" min="0" step=".01" value={form.unit_price} onChange={(e) => change('unit_price', e.target.value)} placeholder="0.00" /></div></label>
        </div>
        <label><span>Expiration date <em>Optional</em></span><input name="expiration_date" type="date" value={form.expiration_date || ''} onChange={(e) => change('expiration_date', e.target.value)} /></label>
        <label>
          <span>Alternative names <em>Optional</em></span>
          {form.alternative_names.map((n, i) => (
            <div className="alt-row" key={i}>
              <input value={n} onChange={(e) => setAlt(i, e.target.value)} placeholder="e.g. Coke" aria-label={`Alternative name ${i + 1}`} />
              {i > 0 && <button type="button" aria-label="Remove name" onClick={() => change('alternative_names', form.alternative_names.filter((_, x) => x !== i))}><X size={17} /></button>}
            </div>
          ))}
        </label>
        <button type="button" className="text-button" onClick={() => change('alternative_names', [...form.alternative_names, ''])}><Plus size={16} /> Add another name</button>
        <div className="modal-actions">
          <Button kind="secondary" onClick={() => navigate('/app/products')}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save product'}</Button>
        </div>
      </form>
    </>
  )
}
