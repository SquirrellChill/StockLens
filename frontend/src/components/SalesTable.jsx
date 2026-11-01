import { formatCurrency, formatDate } from '../utils/formatCurrency'

/** Each sold product shows quantity × price per unit = line total. */
export default function SalesTable({ sales }) {
  return (
    <div className="table">
      <div className="tr th sale-row"><span>Date</span><span>Items (qty × price per unit)</span><span>Units</span><span>Total</span></div>
      {sales.map((s) => (
        <div className="tr sale-row" key={s.id}>
          <span>{formatDate(s.date)}</span>
          <ul className="line-items">
            {s.items.map((i, n) => (
              <li key={n}>
                <span className="li-name">{i.name}</span>
                <span className="li-calc">{i.quantity} × {formatCurrency(i.unit_price)} <em>per unit</em> = <b>{formatCurrency(i.quantity * i.unit_price)}</b></span>
              </li>
            ))}
          </ul>
          <span>{s.items.reduce((n, i) => n + i.quantity, 0)}</span>
          <span><b>{formatCurrency(s.total)}</b></span>
        </div>
      ))}
    </div>
  )
}
