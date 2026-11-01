import { api, ApiError, USE_MOCK } from './api'
import { uid, userRead, userWrite } from './mockDb'

/*
 * A "draft" is the list of items the owner is recording today. Stock only
 * changes when the draft is confirmed.
 * Draft item: { product_id, name, quantity, unit_price }
 */

export const salesService = {
  getDraft() {
    return userRead('sales-draft')
  },

  saveDraft(items) {
    userWrite('sales-draft', items)
  },

  addToDraft(product, quantity = 1) {
    const draft = salesService.getDraft()
    const qty = Math.max(1, Math.floor(Number(quantity) || 1))
    const existing = draft.find((i) => String(i.product_id) === String(product.id))
    if (existing) existing.quantity += qty
    else draft.push({ product_id: product.id, name: product.name, quantity: qty, unit_price: Number(product.unit_price) })
    salesService.saveDraft(draft)
    return draft
  },

  clearDraft() {
    salesService.saveDraft([])
  },

  /** Validates against current stock, deducts it and records the sale. */
  async confirm(items) {
    if (!items.length) throw new ApiError('Add at least one item before confirming.')
    if (!USE_MOCK) {
      const res = await api.post('/api/sales', { items })
      salesService.clearDraft()
      return res
    }
    const products = userRead('products')
    for (const item of items) {
      const p = products.find((x) => String(x.id) === String(item.product_id))
      if (!p) throw new ApiError(`“${item.name}” no longer exists in your inventory.`)
      if (item.quantity > p.quantity) throw new ApiError(`Not enough stock for “${p.name}” (only ${p.quantity} left).`)
    }
    for (const item of items) {
      const p = products.find((x) => String(x.id) === String(item.product_id))
      p.quantity -= item.quantity
    }
    const sale = {
      id: uid(),
      date: new Date().toISOString(),
      items,
      total: items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0),
    }
    userWrite('products', products)
    userWrite('sales', [sale, ...userRead('sales')])
    salesService.clearDraft()
    return sale
  },

  async list() {
    if (!USE_MOCK) {
      const d = await api.get('/api/sales')
      return Array.isArray(d) ? d : d?.items || []
    }
    return userRead('sales')
  },
}
