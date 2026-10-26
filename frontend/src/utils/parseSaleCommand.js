const WORDS = {
  a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17,
  eighteen: 18, nineteen: 19, twenty: 20,
}

const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim()

function namesOf(product) {
  return [product.name, ...(product.alternative_names || [])].map(norm).filter(Boolean)
}

function findProduct(text, products) {
  const t = norm(text)
  if (!t) return null
  let best = null
  for (const p of products) {
    for (const n of namesOf(p)) {
      if (t === n || t.includes(n) || n.includes(t)) {
        if (!best || n.length > best.len) best = { product: p, len: n.length }
      }
    }
  }
  return best?.product || null
}

/**
 * Turns "sold three coca cola and 2 chips" into
 * { matched: [{ product, quantity }], unmatched: ['...'] }
 */
export function parseSaleCommand(transcript, products) {
  const cleaned = norm(transcript).replace(/^(i )?(sold|sell|sale of|add|record)\s+/, '')
  const parts = cleaned.split(/\s*(?:,| and | plus )\s*/).filter(Boolean)
  const matched = []
  const unmatched = []
  for (const part of parts) {
    const tokens = part.split(' ')
    let quantity = 1
    let rest = tokens
    const first = tokens[0]
    if (/^\d+$/.test(first)) { quantity = parseInt(first, 10); rest = tokens.slice(1) }
    else if (first in WORDS) { quantity = WORDS[first]; rest = tokens.slice(1) }
    const product = findProduct(rest.join(' '), products)
    if (product) matched.push({ product, quantity })
    else unmatched.push(part)
  }
  return { matched, unmatched }
}
