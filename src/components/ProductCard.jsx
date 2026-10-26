import { Pencil, Trash2 } from 'lucide-react'
import { formatCurrency, formatDate } from '../utils/formatCurrency'
import { isLowStock } from '../services/productService'

/** One row of the products table. */
export default function ProductCard({ product, onEdit, onDelete }) {
  return (
    <div className="tr">
      <span className="product-name">
        <b className="product-avatar">{product.name?.[0]?.toUpperCase()}</b>
        <i><strong>{product.name}</strong><small>{product.alternative_names?.join(', ') || 'No alternative names'}</small></i>
      </span>
      <span><b>{product.quantity}</b> units {isLowStock(product) && <em className="status low">Low</em>}</span>
      <span>{formatCurrency(product.unit_price)}</span>
      <span>{formatDate(product.expiration_date)}</span>
      <span className="actions">
        <button type="button" aria-label={`Edit ${product.name}`} onClick={() => onEdit(product)}><Pencil size={17} /></button>
        <button type="button" aria-label={`Delete ${product.name}`} className="danger" onClick={() => onDelete(product)}><Trash2 size={17} /></button>
      </span>
    </div>
  )
}
