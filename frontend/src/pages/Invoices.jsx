import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { ReceiptText, Upload } from 'lucide-react'
import Button from '../components/Button'
import InvoiceTable from '../components/InvoiceTable'
import { EmptyState, ErrorNotice, Loader } from '../components/Feedback'
import { invoiceService } from '../services/invoiceService'

export default function Invoices() {
  const navigate = useNavigate()
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    invoiceService.list().then(setInvoices).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [])
  useEffect(load, [load])

  const action = <Button icon={Upload} onClick={() => navigate('/app/invoices/upload')}>Upload invoice</Button>

  return (
    <>
      <div className="title-row"><div><h1>Invoices</h1><p>Supplier invoices you have added to stock.</p></div>{action}</div>
      {error && <ErrorNotice title="Unable to load invoices" message={error} onRetry={load} />}
      <section className="panel table-panel">
        {loading ? <Loader /> : invoices.length
          ? <InvoiceTable invoices={invoices} />
          : <EmptyState icon={ReceiptText} title="No invoices yet" text="Upload a supplier invoice to add stock." action={action} />}
      </section>
    </>
  )
}
