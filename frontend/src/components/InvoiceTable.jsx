import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { formatCurrency, formatDate } from '../utils/formatCurrency'

/** Click a row to see every product with its price per unit and line total. */
export default function InvoiceTable({ invoices }) {
  const [open, setOpen] = useState(() => new Set())
  const toggle = (id) => setOpen((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next })

  return (
    <div className="table">
      <div className="tr th invoice-row"><span>Supplier</span><span>Invoice no.</span><span>Date</span><span>Total</span></div>
      {invoices.map((inv) => {
        const items = inv.items || []
        const expanded = open.has(inv.id)
        return (
          <div className="row-group" key={inv.id}>
            <div className="tr invoice-row">
              <span>
                <button type="button" className="row-toggle" aria-expanded={expanded} disabled={!items.length} onClick={() => toggle(inv.id)}>
                  <ChevronDown size={15} className={expanded ? 'open' : ''} />
                  <span><strong>{inv.supplier}</strong><br /><small>{items.length} item{items.length === 1 ? '' : 's'}{items.length ? (expanded ? ' · hide' : ' · show prices') : ''}</small></span>
                </button>
              </span>
              <span>{inv.invoice_number}</span>
              <span>{formatDate(inv.date)}</span>
              <span><b>{formatCurrency(inv.total)}</b></span>
            </div>
            {expanded && (
              <ul className="line-items detail">
                {items.map((i, n) => (
                  <li key={n}>
                    <span className="li-name">{i.name}</span>
                    <span className="li-calc">{i.quantity} × {formatCurrency(i.unit_price)} <em>per unit</em> = <b>{formatCurrency(i.quantity * i.unit_price)}</b></span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}
