import { useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, ChevronDown, FilePlus2, ImageUp, LoaderCircle, Plus, RefreshCw, Trash2 } from 'lucide-react'
import Modal from './Modal'
import { draftProblems, draftTotal, invoiceService, rowProblem } from '../services/invoiceService'
import { formatCurrency } from '../utils/formatCurrency'
import { USE_MOCK } from '../services/api'
import { uid } from '../services/mockDb'

const blank = () => ({ key: uid(), name: '', quantity: 1, unit_price: '' })
const ENGINE = { claude: 'Read with AI', tesseract: 'Basic reading', none: 'Manual' }

export default function InvoiceDraftCard({ draft, index, total }) {
  const [open, setOpen] = useState(true)
  const [zoom, setZoom] = useState(null)
  const [fileError, setFileError] = useState('')
  const replaceRef = useRef(null)
  const pageRef = useRef(null)
  const { id, status, photos, items } = draft
  const reading = status === 'reading'
  const saved = status === 'saved'
  const problems = status === 'ready' ? draftProblems(draft) : 0
  const sum = draftTotal(draft)

  const set = (patch) => invoiceService.update(id, patch)
  const setItem = (key, field, value) => set({ items: items.map((it) => (it.key === key ? { ...it, [field]: value } : it)) })
  const pick = (action) => (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) setFileError(action(id, file))
  }

  return (
    <article className={`draft-card ${saved ? 'is-saved' : ''}`}>
      <header className="draft-head">
        <button type="button" className="thumb" onClick={() => setZoom(photos[0])} aria-label="View invoice photo">
          <img src={photos[0]?.preview} alt="" />
          {photos.length > 1 && <i>{photos.length}</i>}
        </button>
        <div className="draft-title">
          <strong>Invoice {index + 1} <span>of {total}</span></strong>
          <small>{photos.map((p) => p.name).join(', ')}</small>
        </div>
        <div className="draft-meta">
          {reading && <span className="chip busy"><LoaderCircle size={13} className="spin" /> Reading…</span>}
          {status === 'error' && <span className="chip bad"><AlertTriangle size={13} /> Couldn’t read</span>}
          {saved && <span className="chip ok"><CheckCircle2 size={13} /> Saved</span>}
          {status === 'ready' && !USE_MOCK && draft.engine && <span className={`chip ${draft.engine === 'claude' ? 'ok' : ''}`}>{ENGINE[draft.engine] || draft.engine}</span>}
          {status === 'ready' && <span className="chip">{draftTotalLabel(items, sum)}</span>}
          {problems > 0 && <span className="chip bad">{problems} to fix</span>}
        </div>
        {!saved && <button type="button" className="icon-button" aria-label="Remove this invoice" onClick={() => invoiceService.remove(id)}><Trash2 size={16} /></button>}
        {!saved && status === 'ready' && <button type="button" className={`icon-button chevron ${open ? 'open' : ''}`} aria-label={open ? 'Collapse' : 'Expand'} onClick={() => setOpen(!open)}><ChevronDown size={17} /></button>}
      </header>

      {reading && items.length === 0 && <div className="draft-body"><p className="muted-line"><LoaderCircle size={15} className="spin" /> Reading every line of this invoice. You can keep adding photos or review the others meanwhile.</p></div>}

      {status === 'error' && (
        <div className="draft-body">
          <div className="form-error" role="alert">{draft.error}</div>
          <div className="draft-actions">
            <button type="button" className="text-button" onClick={() => invoiceService.retry(id)}><RefreshCw size={15} /> Try again</button>
            <button type="button" className="text-button" onClick={() => replaceRef.current?.click()}><ImageUp size={15} /> Use a different photo</button>
          </div>
        </div>
      )}

      {status === 'ready' && open && (
        <div className="draft-body">
          {draft.error && <div className="notice warning" role="alert"><AlertTriangle size={17} /><div><strong>That photo couldn’t be read</strong><p>{draft.error} Your previous values were kept.</p></div></div>}
          {draft.warnings?.length > 0 && (
            <div className="notice warning" role="status">
              <AlertTriangle size={17} />
              <div><strong>Please double-check</strong><ul className="warn-list">{draft.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></div>
            </div>
          )}
          <div className="field-row">
            <label>Supplier<input value={draft.supplier} onChange={(e) => set({ supplier: e.target.value })} placeholder="e.g. Fresh Foods Co." /></label>
            <label>Invoice number<input value={draft.invoice_number} onChange={(e) => set({ invoice_number: e.target.value })} placeholder="e.g. INV-1042" /></label>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="review-table">
              <thead><tr><th>Item</th><th style={{ width: 100 }}>Qty</th><th style={{ width: 130 }}>Unit price</th><th style={{ width: 44 }} /></tr></thead>
              <tbody>
                {items.map((it) => {
                  const problem = rowProblem(it)
                  return (
                    <tr key={it.key} className={problem ? 'row-bad' : ''} title={problem || undefined}>
                      <td><input aria-label="Item name" value={it.name} onChange={(e) => setItem(it.key, 'name', e.target.value)} placeholder="Item name" /></td>
                      <td><input aria-label="Quantity" type="number" min="1" step="1" value={it.quantity} onChange={(e) => setItem(it.key, 'quantity', e.target.value)} /></td>
                      <td><input aria-label="Unit price" type="number" min="0" step="any" value={it.unit_price} onChange={(e) => setItem(it.key, 'unit_price', e.target.value)} placeholder="0.00" /></td>
                      <td><button type="button" aria-label="Remove item" className="icon-button" onClick={() => set({ items: items.filter((x) => x.key !== it.key) })}><Trash2 size={16} /></button></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {problems > 0 && <p className="row-hint">Rows outlined in red need a name, a whole quantity and a price.</p>}
          <div className="draft-actions">
            <button type="button" className="text-button" onClick={() => set({ items: [...items, blank()] })}><Plus size={16} /> Add item</button>
            {!USE_MOCK && <>
              <button type="button" className="text-button" onClick={() => replaceRef.current?.click()}><ImageUp size={15} /> Re-upload photo</button>
              <button type="button" className="text-button" onClick={() => pageRef.current?.click()}><FilePlus2 size={15} /> Add another page</button>
            </>}
          </div>
          {fileError && <div className="form-error" role="alert" style={{ marginTop: 10 }}>{fileError}</div>}
          <div className="draft-total"><span>Invoice total{draft.printed_total ? <small> (printed: {draft.printed_total.toLocaleString()}{draft.currency ? ` ${draft.currency}` : ''})</small> : null}</span><span>{formatCurrency(sum)}</span></div>
        </div>
      )}

      {draft.saveError && <div className="form-error" role="alert" style={{ margin: '0 18px 16px' }}>{draft.saveError}</div>}

      <input ref={replaceRef} type="file" accept="image/*" hidden onChange={pick(invoiceService.replacePhoto)} />
      <input ref={pageRef} type="file" accept="image/*" hidden onChange={pick(invoiceService.addPage)} />

      {zoom && (
        <Modal onClose={() => setZoom(null)} className="lightbox" label="Invoice photo">
          <div className="lightbox-photos">{photos.map((p) => <img key={p.id} src={p.preview} alt={p.name} />)}</div>
          <div className="modal-actions"><button type="button" className="button secondary" onClick={() => setZoom(null)}>Close</button></div>
        </Modal>
      )}
    </article>
  )
}

function draftTotalLabel(items, sum) {
  const n = items.filter((i) => String(i.name || '').trim()).length
  return `${n} item${n === 1 ? '' : 's'} · ${formatCurrency(sum)}`
}
