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
        </div>
      </section>
    </>
  )
}
