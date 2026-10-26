import { api, USE_MOCK } from './api'
import { userRead } from './mockDb'
import { isLowStock } from './productService'
import { formatCurrency, formatDate } from '../utils/formatCurrency'

export const dashboardService = {
  async summary() {
    if (!USE_MOCK) return api.get('/api/dashboard')

    const products = userRead('products')
    const sales = userRead('sales')
    const invoices = userRead('invoices')
    const today = new Date().toDateString()
    const todaySales = sales
      .filter((s) => new Date(s.date).toDateString() === today)
      .reduce((sum, s) => sum + s.total, 0)
    const lowStock = products.filter(isLowStock)

    const recent = [
      ...sales.map((s) => ({ date: s.date, title: `Sale · ${s.items.length} item${s.items.length === 1 ? '' : 's'}`, amount: formatCurrency(s.total) })),
      ...invoices.map((i) => ({ date: i.date, title: `Invoice · ${i.supplier}`, amount: formatCurrency(i.total) })),
    ]
      .sort((a, b) => new Date(b.date) - new Date(a.date))
      .slice(0, 5)
      .map((a) => ({ ...a, date: formatDate(a.date) }))

    return {
      total_products: products.length,
      today_sales: todaySales,
      low_stock: lowStock.length,
      low_stock_items: lowStock.slice(0, 5),
      recent_activity: recent,
    }
  },
}
