import { api, ApiError, USE_MOCK } from './api'
import { uid, userRead, userWrite } from './mockDb'

/*
 * Invoice flow: upload -> review -> confirm.
 * The staged invoice is kept in memory only (images are too large for storage).
 * Invoice item: { name, quantity, unit_price }
 */

let staged = null

export const invoiceService = {
  stage(file) {
    if (staged?.preview) URL.revokeObjectURL(staged.preview)
    staged = { file, preview: URL.createObjectURL(file), supplier: '', invoice_number: '', items: [] }
    return staged
  },

  getStaged() {
    return staged
  },

  updateStaged(patch) {
    if (staged) staged = { ...staged, ...patch }
    return staged
  },

  discardStaged() {
    if (staged?.preview) URL.revokeObjectURL(staged.preview)
    staged = null
  },

  /**
   * With a backend: OCR runs server-side (/api/invoices/extract).
   * Without one there is no OCR, so the owner types the lines in on the review page.
   */
  async extract() {
    if (!staged) throw new ApiError('Please upload an invoice image first.')
    if (!USE_MOCK) {
      const fd = new FormData()
      fd.append('file', staged.file)
      const data = await api.upload('/api/invoices/extract', fd)
      staged = {
        ...staged,
        supplier: data?.supplier || '',
        invoice_number: data?.invoice_number || '',
        items: (data?.items || []).map((i) => ({ name: i.name || '', quantity: i.quantity ?? 1, unit_price: i.unit_price ?? 0 })),
      }
    }
    return staged
  },

  async confirm({ supplier, invoice_number, items }) {
    const lines = items
      .map((i) => ({ name: String(i.name || '').trim(), quantity: Number(i.quantity), unit_price: Number(i.unit_price) }))
      .filter((i) => i.name)
    if (!lines.length) throw new ApiError('Add at least one item before confirming.')
    if (lines.some((i) => !(i.quantity > 0) || !(i.unit_price >= 0))) throw new ApiError('Every item needs a quantity above 0 and a valid price.')

    if (!USE_MOCK) return api.post('/api/invoices', { supplier, invoice_number, items: lines })

    const products = userRead('products')
    for (const line of lines) {
      const existing = products.find((p) => [p.name, ...(p.alternative_names || [])].some((n) => n.toLowerCase() === line.name.toLowerCase()))
      if (existing) { existing.quantity += line.quantity; existing.unit_price = line.unit_price || existing.unit_price }
      else products.unshift({ id: uid(), name: line.name, quantity: line.quantity, unit_price: line.unit_price, expiration_date: '', alternative_names: [] })
    }
    const invoice = {
      id: uid(),
      date: new Date().toISOString(),
      supplier: supplier?.trim() || 'Unknown supplier',
      invoice_number: invoice_number?.trim() || '—',
      items: lines,
      total: lines.reduce((s, i) => s + i.quantity * i.unit_price, 0),
    }
    userWrite('products', products)
    userWrite('invoices', [invoice, ...userRead('invoices')])
    invoiceService.discardStaged()
    return invoice
  },

  async list() {
    if (!USE_MOCK) {
      const d = await api.get('/api/invoices')
      return Array.isArray(d) ? d : d?.items || []
    }
    return userRead('invoices')
  },
}
