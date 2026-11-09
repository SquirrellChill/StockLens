/**
 * Returns a human-readable problem if `wanted` units of `product` cannot be sold
 * (given `alreadyDrafted` units already in today's draft), otherwise ''.
 */
export function stockProblem(product, wanted, alreadyDrafted = 0) {
  const stock = Number(product.quantity) || 0
  if (stock <= 0) return `“${product.name}” is out of stock.`
  const available = stock - alreadyDrafted
  if (available <= 0) return `All ${stock} “${product.name}” in stock are already in today’s sales.`
  if (wanted > available) return `Only ${available} “${product.name}” left${alreadyDrafted ? ' to add' : ''} — you asked for ${wanted}.`
  return ''
}
