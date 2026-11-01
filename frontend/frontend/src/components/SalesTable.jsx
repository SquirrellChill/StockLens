import { formatCurrency, formatDate } from '../utils/formatCurrency'

export default function SalesTable({ sales }) {
  return (
    <div className="table">
      <div className="tr th sale-row"><span>Date</span><span>Items</span><span>Units</span><span>Total</span></div>
      {sales.map((s) => (
        <div className="tr sale-row" key={s.id}>
          <span>{formatDate(s.date)}</span>
          <span>{s.items.map((i) => `${i.quantity}× ${i.name}`).join(', ')}</span>
          <span>{s.items.reduce((n, i) => n + i.quantity, 0)}</span>
          <span><b>{formatCurrency(s.total)}</b></span>
        </div>
      ))}
    </div>
  )
}
