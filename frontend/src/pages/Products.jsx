import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { Boxes, Plus, Search } from 'lucide-react'
import Button from '../components/Button'
import Modal from '../components/Modal'
import ProductCard from '../components/ProductCard'
import { EmptyState, ErrorNotice, Loader } from '../components/Feedback'
import { isExpiringSoon, isLowStock, productService } from '../services/productService'

const FILTERS = ['All', 'Low stock', 'Expiring soon']

export default function Products() {
  const navigate = useNavigate()
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    productService.list().then(setProducts).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [])
  useEffect(load, [load])

  const shown = useMemo(() => {
    const q = search.trim().toLowerCase()
    return products.filter((p) => {
      const matches = !q || `${p.name} ${(p.alternative_names || []).join(' ')}`.toLowerCase().includes(q)
      const passes = filter === 'All' || (filter === 'Low stock' && isLowStock(p)) || (filter === 'Expiring soon' && isExpiringSoon(p))
      return matches && passes
    })
  }, [products, search, filter])

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await productService.remove(toDelete.id)
      setToDelete(null)
      load()
    } catch (e) {
      setToDelete(null)
      setError(e.message)
    } finally {
      setDeleting(false)
    }
  }

  const addButton = <Button icon={Plus} onClick={() => navigate('/app/products/new')}>Add product</Button>

  return (
    <>
      <div className="title-row"><div><h1>Products</h1><p>Manage products and keep track of your stock.</p></div>{addButton}</div>
      <div className="toolbar">
        <div className="search"><Search size={18} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search products or alternative names" aria-label="Search products" /></div>
        <div className="filter-tabs">{FILTERS.map((x) => <button key={x} className={filter === x ? 'active' : ''} onClick={() => setFilter(x)}>{x}</button>)}</div>
      </div>
      {error && <ErrorNotice title="Something went wrong" message={error} onRetry={load} />}
      <section className="panel table-panel">
        {loading ? <Loader /> : shown.length ? (
          <div className="table">
            <div className="tr th"><span>Product name</span><span>Quantity</span><span>Unit price</span><span>Expiration date</span><span>Actions</span></div>
            {shown.map((p) => <ProductCard key={p.id} product={p} onEdit={(x) => navigate(`/app/products/${x.id}/edit`)} onDelete={setToDelete} />)}
          </div>
        ) : (
          <EmptyState
            icon={Boxes}
            title={search || filter !== 'All' ? 'No products found' : 'Your inventory is empty'}
            text={search || filter !== 'All' ? 'Try another search term or filter.' : 'Add your first product to get started.'}
            action={addButton}
          />
        )}
      </section>

      {toDelete && (
        <Modal onClose={() => setToDelete(null)} className="confirm-modal" label="Delete product">
          <h2>Delete “{toDelete.name}”?</h2>
          <p>This removes the product from your inventory.</p>
          <div className="modal-actions">
            <Button kind="secondary" onClick={() => setToDelete(null)}>Cancel</Button>
            <Button kind="danger" disabled={deleting} onClick={confirmDelete}>{deleting ? 'Deleting…' : 'Delete'}</Button>
          </div>
        </Modal>
      )}
    </>
  )
}
