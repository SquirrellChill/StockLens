import { api, ApiError, USE_MOCK } from './api'
import { uid, userRead, userWrite } from './mockDb'

/*
 * Invoice flow: upload (one or many photos) -> review -> confirm.
 *
 * Every photo becomes a "draft" kept in memory only (images are too large for storage). Drafts are read
 * by the backend a few at a time in the background, so the owner can keep adding photos or start
 * reviewing the finished ones. Nothing touches stock until a draft is confirmed.
 *
 * draft: {
 *   id, status: 'reading' | 'ready' | 'error' | 'saved',
 *   photos: [{ id, name, preview, file }],   // first photo = the invoice, extra photos = more pages
 *   supplier, invoice_number, items: [{ key, name, quantity, unit_price }],
 *   engine, currency, printed_total, warnings: [], error, saveError
 * }
 */

export const MAX_BYTES = 10 * 1024 * 1024
export const MAX_DRAFTS = 30
const CONCURRENCY = 3
const READ_TIMEOUT_MS = 150_000

let drafts = []
let queue = []
let active = 0
const listeners = new Set()

const emit = () => { drafts = [...drafts]; listeners.forEach((l) => l()) }
const find = (id) => drafts.find((d) => d.id === id)
const patch = (id, changes) => {
  drafts = drafts.map((d) => (d.id === id ? { ...d, ...(typeof changes === 'function' ? changes(d) : changes) } : d))
  listeners.forEach((l) => l())
}
const makeItem = (i = {}) => ({ key: uid(), name: i.name || '', quantity: i.quantity ?? 1, unit_price: i.unit_price ?? '' })
const makePhoto = (file) => ({ id: uid(), name: file.name || 'photo', preview: URL.createObjectURL(file), file })

export function validateFile(file) {
  if (!file.type?.startsWith('image/')) return `“${file.name}” isn’t an image. Please choose JPG, PNG or HEIC photos.`
  if (file.size > MAX_BYTES) return `“${file.name}” is larger than 10 MB.`
  return ''
}

/** Rows the owner still has to fix before saving. A completely blank row is ignored. */
export function rowProblem(item) {
  const name = String(item.name || '').trim()
  const blank = !name && (item.unit_price === '' || item.unit_price == null)
  if (blank) return ''
  if (!name) return 'Item name is required'
  const qty = Number(item.quantity)
  if (!Number.isInteger(qty) || qty < 1) return 'Quantity must be a whole number, 1 or more'
  const price = Number(item.unit_price)
  if (item.unit_price === '' || !Number.isFinite(price) || price < 0) return 'Enter a valid price'
  return ''
}

export const draftLines = (d) => d.items.filter((i) => !(String(i.name || '').trim() === '' && (i.unit_price === '' || i.unit_price == null)))
export const draftProblems = (d) => draftLines(d).filter((i) => rowProblem(i)).length
export const draftTotal = (d) => d.items.reduce((s, i) => s + (Number(i.quantity) || 0) * (Number(i.unit_price) || 0), 0)

async function readPhoto(file) {
  const fd = new FormData()
  fd.append('file', file)
  const signal = typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(READ_TIMEOUT_MS) : undefined
  try {
    return await api.upload('/api/invoices/extract', fd, { signal })
  } catch (e) {
    if (e?.name === 'TimeoutError' || e?.name === 'AbortError') throw new ApiError('Reading this invoice took too long. Please try again.')
    if (e instanceof ApiError) throw e
    throw new ApiError('Unable to connect. Check your connection and try again.')
  }
}

const jobsOf = new Map() // draftId -> Set(jobId) of reads queued or running for that draft
let jobCounter = 0

/** reading while any read is pending; error only when there is nothing to show; otherwise ready. */
function refresh(id) {
  const d = find(id)
  if (!d || d.status === 'saved') return
  const status = jobsOf.has(id) ? 'reading' : (d.items.length === 0 && d.error ? 'error' : 'ready')
  if (status !== d.status) patch(id, { status })
}

function finishJob(job) {
  const set = jobsOf.get(job.draftId)
  if (set) { set.delete(job.id); if (!set.size) jobsOf.delete(job.draftId) }
  refresh(job.draftId)
}

async function runJob(job) {
  const { draftId, photoId, mode } = job
  try {
    const photo = find(draftId)?.photos.find((p) => p.id === photoId)
    if (!photo) return // removed or replaced before it ran
    const data = await readPhoto(photo.file)
    if (!find(draftId)?.photos.some((p) => p.id === photoId)) return // removed or replaced while reading
    const items = (data?.items || []).map(makeItem)
    patch(draftId, (cur) => {
      const kept = cur.items.filter((i) => String(i.name || '').trim() || (i.unit_price !== '' && i.unit_price != null))
      if (mode === 'append') {
        return {
          items: [...kept, ...items],
          supplier: cur.supplier || data?.supplier || '',
          invoice_number: cur.invoice_number || data?.invoice_number || '',
          warnings: [...cur.warnings, ...(data?.warnings || [])],
          engine: data?.engine || cur.engine, currency: data?.currency || cur.currency,
          printed_total: null, error: '',
        }
      }
      return {
        items: items.length ? items : [makeItem()],
        supplier: data?.supplier || '', invoice_number: data?.invoice_number || '',
        warnings: data?.warnings || [], engine: data?.engine || '', currency: data?.currency || '',
        printed_total: data?.printed_total ?? null, error: '',
      }
    })
  } catch (e) {
    if (find(draftId)) patch(draftId, { error: e.message || 'We couldn’t read this invoice.' })
  } finally {
    finishJob(job)
  }
}

function pump() {
  while (active < CONCURRENCY && queue.length) {
    const job = queue.shift()
    active += 1
    runJob(job).finally(() => { active -= 1; pump() })
  }
}

function enqueue(draftId, photoId, mode) {
  if (USE_MOCK) {
    // No backend, no automatic reading: the owner types the lines in.
    patch(draftId, (cur) => ({ status: 'ready', error: '', items: cur.items.length ? cur.items : [makeItem()] }))
    return
  }
  const job = { id: ++jobCounter, draftId, photoId, mode }
  if (!jobsOf.has(draftId)) jobsOf.set(draftId, new Set())
  jobsOf.get(draftId).add(job.id)
  patch(draftId, { status: 'reading', error: '' })
  queue.push(job)
  pump()
}

/** Forget reads that haven't started yet (their draft was removed or its photo replaced). */
function dropQueued(draftId) {
  queue.filter((j) => j.draftId === draftId).forEach((j) => finishJob(j))
  queue = queue.filter((j) => j.draftId !== draftId)
}

const revoke = (d) => d.photos.forEach((p) => URL.revokeObjectURL(p.preview))
const blankDraft = (photo) => ({
  id: uid(), status: 'reading', photos: [photo], supplier: '', invoice_number: '', items: [],
  engine: '', currency: '', printed_total: null, warnings: [], error: '', saveError: '',
})

async function saveInvoice({ supplier, invoice_number, items, client_ref }) {
  const lines = items
    .map((i) => ({ name: String(i.name || '').trim(), quantity: Number(i.quantity), unit_price: Number(i.unit_price) }))
    .filter((i) => i.name)
  if (!lines.length) throw new ApiError('Add at least one item before confirming.')
  if (lines.some((i) => !Number.isInteger(i.quantity) || i.quantity < 1 || !(i.unit_price >= 0))) {
    throw new ApiError('Every item needs a whole quantity of 1 or more and a valid price.')
  }
  if (!USE_MOCK) return api.post('/api/invoices', { supplier, invoice_number, items: lines, client_ref })

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
  return invoice
}

export const invoiceService = {
  // ---- store (used with useSyncExternalStore) ----
  subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener) },
  getDrafts() { return drafts },

  /** Adds photos as new drafts and starts reading them. Returns messages for any photos that were skipped. */
  addFiles(files) {
    const rejected = []
    for (const file of Array.from(files || [])) {
      const problem = validateFile(file)
      if (problem) { rejected.push(problem); continue }
      if (drafts.filter((d) => d.status !== 'saved').length >= MAX_DRAFTS) { rejected.push(`You can review up to ${MAX_DRAFTS} invoices at a time. Save these first, then add more.`); break }
      const photo = makePhoto(file)
      const draft = blankDraft(photo)
      drafts = [...drafts, draft]
      emit()
      enqueue(draft.id, photo.id, 'replace')
    }
    return rejected
  },

  update(id, changes) { patch(id, changes) },

  /** The photo was unclear: upload another one and read it again, replacing what was read before. */
  replacePhoto(id, file) {
    const problem = validateFile(file)
    if (problem) return problem
    const photo = makePhoto(file)
    const d = find(id)
    if (!d) return ''
    revoke(d)
    dropQueued(id)
    // Keep what was read before until the new photo has been read successfully.
    patch(id, { photos: [photo], saveError: '' })
    enqueue(id, photo.id, 'replace')
    return ''
  },

  /** The invoice has more pages (or part of it was cut off): read another photo and add its items. */
  addPage(id, file) {
    const problem = validateFile(file)
    if (problem) return problem
    const photo = makePhoto(file)
    patch(id, (cur) => ({ photos: [...cur.photos, photo] }))
    enqueue(id, photo.id, 'append')
    return ''
  },

  retry(id) {
    const d = find(id)
    if (!d) return
    enqueue(id, d.photos[0].id, 'replace')
  },

  remove(id) {
    const d = find(id)
    if (!d) return
    revoke(d)
    dropQueued(id)
    drafts = drafts.filter((x) => x.id !== id)
    emit()
  },

  /** Throw away everything (Cancel). */
  clear() {
    drafts.forEach(revoke)
    queue = []
    jobsOf.clear()
    drafts = []
    emit()
  },

  /** Forget invoices that were already saved. */
  dropSaved() {
    if (!drafts.some((d) => d.status === 'saved')) return
    drafts.filter((d) => d.status === 'saved').forEach(revoke)
    drafts = drafts.filter((d) => d.status !== 'saved')
    emit()
  },

  /**
   * Saves every finished draft, one after another. A draft that fails stays on screen with its error;
   * the ones that worked are marked saved. Retrying is safe: each draft carries its own idempotency key.
   */
  async confirmAll() {
    let saved = 0
    let failed = 0
    for (const draft of drafts.filter((d) => d.status === 'ready')) {
      const d = find(draft.id)
      if (!d || d.status !== 'ready') continue
      if (draftProblems(d)) { failed += 1; patch(d.id, { saveError: 'Fix the highlighted rows first.' }); continue }
      patch(d.id, { saveError: '' })
      try {
        await saveInvoice({ supplier: d.supplier, invoice_number: d.invoice_number, items: d.items, client_ref: d.id })
        patch(d.id, { status: 'saved' })
        saved += 1
      } catch (e) {
        failed += 1
        patch(d.id, { saveError: e.message || 'Could not save this invoice. Please try again.' })
      }
    }
    return { saved, failed }
  },

  async list() {
    if (!USE_MOCK) {
      const d = await api.get('/api/invoices')
      return Array.isArray(d) ? d : d?.items || []
    }
    return userRead('invoices')
  },
}
