import { api, ApiError, USE_MOCK } from './api'
import { uid, userRead, userWrite } from './mockDb'

const clean = (p) => ({
  name: String(p.name).trim(),
  quantity: Number(p.quantity),
  unit_price: Number(p.unit_price),
  expiration_date: p.expiration_date || '',
  alternative_names: (p.alternative_names || []).map((n) => String(n).trim()).filter(Boolean),
})

export const productService = {
  async list() {
    if (!USE_MOCK) {
      const d = await api.get('/api/products')
      return Array.isArray(d) ? d : d?.items || []
    }
    return userRead('products')
  },

  async get(id) {
    if (!USE_MOCK) return api.get(`/api/products/${id}`)
    const p = userRead('products').find((x) => String(x.id) === String(id))
    if (!p) throw new ApiError('Product not found.', 404)
    return p
  },

  async create(data) {
    if (!USE_MOCK) return api.post('/api/products', clean(data))
    const list = userRead('products')
    const product = { id: uid(), ...clean(data) }
    userWrite('products', [product, ...list])
    return product
  },

  async update(id, data) {
    if (!USE_MOCK) return api.put(`/api/products/${id}`, clean(data))
    const list = userRead('products')
    const i = list.findIndex((x) => String(x.id) === String(id))
    if (i < 0) throw new ApiError('Product not found.', 404)
    list[i] = { ...list[i], ...clean(data) }
    userWrite('products', list)
    return list[i]
  },

  async remove(id) {
    if (!USE_MOCK) return api.delete(`/api/products/${id}`)
    userWrite('products', userRead('products').filter((x) => String(x.id) !== String(id)))
  },
}

export const LOW_STOCK_THRESHOLD = 5
export const isLowStock = (p) => Number(p.quantity) <= LOW_STOCK_THRESHOLD
export const isExpiringSoon = (p) =>
  !!p.expiration_date && new Date(p.expiration_date).getTime() - Date.now() < 14 * 864e5
