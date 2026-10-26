import { useCallback, useEffect, useState } from 'react'
import { History as HistoryIcon } from 'lucide-react'
import InvoiceTable from '../components/InvoiceTable'
import SalesTable from '../components/SalesTable'
import { EmptyState, ErrorNotice, Loader } from '../components/Feedback'
import { invoiceService } from '../services/invoiceService'
import { salesService } from '../services/salesService'

export default function History() {
  const [tab, setTab] = useState('Invoices')
  const [data, setData] = useState({ Invoices: [], Sales: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    Promise.all([invoiceService.list(), salesService.list()])
      .then(([Invoices, Sales]) => setData({ Invoices, Sales }))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])
  useEffect(load, [load])

  const rows = data[tab]

  return (
    <>
      <div className="title-row"><div><h1>History</h1><p>Review confirmed invoices and sales.</p></div></div>
      {error && <ErrorNotice title="Unable to load history" message={error} onRetry={load} />}
      <section className="panel generic-panel table-panel">
        <div className="filter-tabs page-tabs">{['Invoices', 'Sales'].map((x) => <button key={x} className={tab === x ? 'active' : ''} onClick={() => setTab(x)}>{x}</button>)}</div>
        {loading ? <Loader /> : rows.length
          ? (tab === 'Invoices' ? <InvoiceTable invoices={rows} /> : <SalesTable sales={rows} />)
          : <EmptyState icon={HistoryIcon} title={`No ${tab.toLowerCase()} yet`} text="Confirmed records will appear here." />}
      </section>
    </>
  )
}
