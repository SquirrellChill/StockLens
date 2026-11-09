<<<<<<< HEAD
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useEffect } from 'react'
import { AlertTriangle, CheckCircle2, ChevronRight, ImagePlus, LoaderCircle, Upload, X } from 'lucide-react'
import Button from '../components/Button'
import { useInvoiceDrafts } from '../hooks/useInvoiceDrafts'
import { invoiceService, MAX_DRAFTS } from '../services/invoiceService'
import { USE_MOCK } from '../services/api'

export default function InvoiceUpload() {
  const navigate = useNavigate()
  const drafts = useInvoiceDrafts().filter((d) => d.status !== 'saved')
  const [errors, setErrors] = useState([])
  const [dragging, setDragging] = useState(false)
  const pickRef = useRef(null)

  useEffect(() => { invoiceService.dropSaved() }, [])

  const add = (files) => {
    if (!files?.length) return
    setErrors(invoiceService.addFiles(files))
  }
  const cancel = () => { invoiceService.clear(); navigate('/app/invoices') }
  const reading = drafts.filter((d) => d.status === 'reading').length

  return (
    <>
      <div className="title-row"><div><h1>Add stock from invoices</h1><p>Upload one or many supplier invoices, then review every item before saving.</p></div></div>
      <section className="flow-card">
        <div className="steps"><b className="active">1<span>Upload</span></b><i /><b>2<span>Review</span></b><i /><b>3<span>Confirm</span></b></div>

        <div
          className={`upload-zone ${dragging ? 'dragging' : ''} ${drafts.length ? 'compact' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); add(e.dataTransfer.files) }}
        >
          <span><ImagePlus size={27} /></span>
          <h2>{drafts.length ? 'Add more invoices' : 'Upload your invoices'}</h2>
          <p>Choose several photos at once, or drop them here. Each photo is one invoice.</p>
          <div>
            <label className="button primary"><Upload size={18} />Upload images<input ref={pickRef} type="file" accept="image/*" multiple onChange={(e) => { add(e.target.files); e.target.value = '' }} /></label>
            <label className="button secondary"><ImagePlus size={18} />Take photo<input type="file" accept="image/*" capture="environment" onChange={(e) => { add(e.target.files); e.target.value = '' }} /></label>
          </div>
          <small>JPG, PNG or HEIC · Up to 10 MB each · Up to {MAX_DRAFTS} invoices</small>
        </div>

        {errors.length > 0 && <div className="form-error" role="alert" style={{ marginTop: 14 }}>{errors.map((m, i) => <div key={i}>{m}</div>)}</div>}

        {drafts.length > 0 && (
          <>
            <div className="batch-head"><strong>{drafts.length} invoice{drafts.length === 1 ? '' : 's'} added</strong>{!USE_MOCK && reading > 0 && <span><LoaderCircle size={13} className="spin" /> Reading {reading}…</span>}</div>
            <div className="batch-grid">
              {drafts.map((d) => (
                <div className="batch-item" key={d.id}>
                  <img src={d.photos[0].preview} alt={d.photos[0].name} />
                  <button type="button" className="batch-remove" aria-label={`Remove ${d.photos[0].name}`} onClick={() => invoiceService.remove(d.id)}><X size={14} /></button>
                  <span className={`batch-status ${d.status}`}>
                    {d.status === 'reading' && <><LoaderCircle size={12} className="spin" /> Reading</>}
                    {d.status === 'ready' && <><CheckCircle2 size={12} /> {USE_MOCK ? 'Added' : 'Read'}</>}
                    {d.status === 'error' && <><AlertTriangle size={12} /> Failed</>}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="flow-actions">
          <Button kind="secondary" onClick={cancel}>Cancel</Button>
          <Button disabled={!drafts.length} onClick={() => navigate('/app/invoices/review')}>
            Review {drafts.length > 1 ? `${drafts.length} invoices` : 'invoice'} <ChevronRight size={17} />
          </Button>
=======
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { ChevronRight, ImagePlus, Upload } from 'lucide-react'
import Button from '../components/Button'
import { invoiceService } from '../services/invoiceService'

const MAX_BYTES = 10 * 1024 * 1024

export default function InvoiceUpload() {
  const navigate = useNavigate()
  const [staged, setStaged] = useState(() => invoiceService.getStaged())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const pick = (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) return setError('Please choose an image file (JPG, PNG or HEIC).')
    if (file.size > MAX_BYTES) return setError('That image is larger than 10 MB. Please choose a smaller one.')
    setError('')
    setStaged({ ...invoiceService.stage(file) })
  }

  const cancel = () => { invoiceService.discardStaged(); setStaged(null); navigate('/app/invoices') }

  const extract = async () => {
    setBusy(true)
    setError('')
    try {
      await invoiceService.extract()
      navigate('/app/invoices/review')
    } catch (e) {
      setError(e.message || 'We couldn’t read this invoice. Please try another image.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="title-row"><div><h1>Add stock from invoice</h1><p>Upload a supplier invoice, then review every item before saving.</p></div></div>
      <section className="flow-card">
        <div className="steps"><b className="active">1<span>Upload</span></b><i /><b>2<span>Review</span></b><i /><b>3<span>Confirm</span></b></div>
        <div className="upload-zone">
          {staged?.preview
            ? <img src={staged.preview} alt="Invoice preview" />
            : <><span><ImagePlus size={27} /></span><h2>Upload your invoice</h2><p>Take a clear photo or choose an image from your device.</p></>}
          <div>
            <label className="button primary"><Upload size={18} />Upload image<input type="file" accept="image/*" onChange={(e) => pick(e.target.files?.[0])} /></label>
            <label className="button secondary"><ImagePlus size={18} />Take photo<input type="file" accept="image/*" capture="environment" onChange={(e) => pick(e.target.files?.[0])} /></label>
          </div>
          <small>JPG, PNG or HEIC · Maximum 10 MB</small>
        </div>
        {error && <div className="form-error" role="alert" style={{ marginTop: 14 }}>{error}</div>}
        <div className="flow-actions">
          <Button kind="secondary" onClick={cancel}>Cancel</Button>
          <Button disabled={!staged || busy} onClick={extract}>{busy ? 'Extracting…' : 'Continue'} <ChevronRight size={17} /></Button>
>>>>>>> origin/main
        </div>
      </section>
    </>
  )
}
