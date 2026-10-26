import { formatCurrency, formatDate } from '../utils/formatCurrency'

export default function InvoiceTable({ invoices }) {
  return (
    <div className="table">
      <div className="tr th invoice-row"><span>Supplier</span><span>Invoice no.</span><span>Date</span><span>Total</span></div>
      {invoices.map((inv) => (
        <div className="tr invoice-row" key={inv.id}>
          <span><strong>{inv.supplier}</strong><br /><small>{inv.items?.length || 0} items</small></span>
          <span>{inv.invoice_number}</span>
          <span>{formatDate(inv.date)}</span>
          <span><b>{formatCurrency(inv.total)}</b></span>
        </div>
      ))}
    </div>
  )
}
