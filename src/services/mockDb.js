// Tiny localStorage "database" used when no backend is configured.
// Everything is namespaced per user so accounts never see each other's data.

const PREFIX = 'stocklens:'

export function read(key, fallback) {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

export function write(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    throw new Error('Browser storage is unavailable or full. Please free some space and try again.')
  }
}

export function remove(key) {
  try { localStorage.removeItem(PREFIX + key) } catch { /* ignore */ }
}

export function uid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export function randomToken(bytes = 24) {
  if (globalThis.crypto?.getRandomValues) {
    const arr = new Uint8Array(bytes)
    globalThis.crypto.getRandomValues(arr)
    return Array.from(arr, (b) => b.toString(16).padStart(2, '0')).join('')
  }
  return Array.from({ length: bytes }, () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')).join('')
}

export function currentUserId() {
  return read('session', null)?.userId || null
}

/** Per-user collection helpers: userRead('products') etc. */
export function userRead(collection, fallback = []) {
  const id = currentUserId()
  return id ? read(`${collection}:${id}`, fallback) : fallback
}

export function userWrite(collection, value) {
  const id = currentUserId()
  if (!id) throw new Error('You are not logged in.')
  write(`${collection}:${id}`, value)
}
