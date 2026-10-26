import { api, ApiError, authPaths, setAccessToken, USE_MOCK } from './api'
import { read, write, remove, uid, randomToken } from './mockDb'
import { isEmail, normalizeEmail, passwordError } from '../utils/validation'

/*
 * Authentication service.
 *  - With VITE_API_BASE_URL set it talks to the FastAPI backend.
 *  - Without it, a local account store (localStorage) provides real
 *    sign-up / login / sessions / password change in the browser only.
 *    Passwords are salted + hashed (PBKDF2), but this is a demo store:
 *    it is NOT a substitute for server-side auth.
 */

const SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000
const RESET_TTL_MS = 30 * 60 * 1000

export const DEMO_ACCOUNT = { email: 'demo@stocklens.app', password: 'Demo1234!' }

const publicUser = (u) => ({ id: u.id, name: u.name, full_name: u.name, email: u.email, provider: 'local' })
const fail = (message, status = 400) => { throw new ApiError(message, status) }

/* ---------- hashing ---------- */

const toHex = (buf) => Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('')

async function hashPassword(password, salt) {
  const subtle = globalThis.crypto?.subtle
  if (subtle) {
    const key = await subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits'])
    const bits = await subtle.deriveBits(
      { name: 'PBKDF2', salt: new TextEncoder().encode(salt), iterations: 120000, hash: 'SHA-256' },
      key,
      256,
    )
    return toHex(bits)
  }
  // Insecure-context fallback (e.g. plain http on a LAN address): non-cryptographic.
  let h = 2166136261
  const s = salt + password
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0 }
  return `fnv-${h.toString(16)}`
}

/* ---------- local store ---------- */

const getUsers = () => read('users', [])
const saveUsers = (users) => write('users', users)

async function makeUser(name, email, password) {
  const salt = randomToken(16)
  return { id: uid(), name: name.trim(), email: normalizeEmail(email), salt, hash: await hashPassword(password, salt), created_at: new Date().toISOString() }
}

let seeding = null
function ensureSeed() {
  if (!seeding) {
    seeding = (async () => {
      if (getUsers().length) return
      const demo = await makeUser('Demo Owner', DEMO_ACCOUNT.email, DEMO_ACCOUNT.password)
      saveUsers([demo])
      write(`products:${demo.id}`, demoProducts())
    })()
  }
  return seeding
}

function demoProducts() {
  const inDays = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10)
  return [
    { id: uid(), name: 'Coca-Cola 500ml', quantity: 48, unit_price: 1.5, expiration_date: inDays(120), alternative_names: ['Coke', 'Coca Cola'] },
    { id: uid(), name: 'Instant Noodles', quantity: 3, unit_price: 0.8, expiration_date: inDays(200), alternative_names: ['Ramen'] },
    { id: uid(), name: 'Whole Milk 1L', quantity: 12, unit_price: 1.9, expiration_date: inDays(6), alternative_names: ['Milk'] },
    { id: uid(), name: 'Potato Chips', quantity: 25, unit_price: 1.2, expiration_date: inDays(90), alternative_names: ['Chips', 'Crisps'] },
    { id: uid(), name: 'Bottled Water 1L', quantity: 4, unit_price: 0.6, expiration_date: '', alternative_names: ['Water'] },
  ]
}

function startSession(user) {
  write('session', { token: randomToken(), userId: user.id, expires_at: Date.now() + SESSION_TTL_MS })
}

function activeSession() {
  const s = read('session', null)
  if (!s) return null
  if (s.expires_at < Date.now()) { remove('session'); return null }
  return s
}

function sessionUser() {
  const s = activeSession()
  if (!s) fail('Your session has expired. Please log in again.', 401)
  const user = getUsers().find((u) => u.id === s.userId)
  if (!user) { remove('session'); fail('Your session has expired. Please log in again.', 401) }
  return user
}

/* ---------- public API ---------- */

function acceptRemote(data) {
  if (data?.access_token) setAccessToken(data.access_token)
  return data
}

export const authService = {
  async me() {
    if (!USE_MOCK) {
      const data = await api.get(authPaths.me, { skipUnauthorizedEvent: true })
      return data?.user || data
    }
    await ensureSeed()
    return publicUser(sessionUser())
  },

  async login(email, password) {
    if (!USE_MOCK) {
      const data = acceptRemote(await api.post(authPaths.login, { email, password }, { skipUnauthorizedEvent: true }))
      return data?.user || (await authService.me())
    }
    await ensureSeed()
    const user = getUsers().find((u) => u.email === normalizeEmail(email))
    const bad = () => fail('Incorrect email or password.', 401)
    if (!user) { await hashPassword(password, 'x'); bad() } // keep timing similar
    if ((await hashPassword(password, user.salt)) !== user.hash) bad()
    startSession(user)
    return publicUser(user)
  },

  async register(fullName, email, password) {
    if (!USE_MOCK) {
      const data = acceptRemote(await api.post(authPaths.register, { full_name: fullName, email, password }, { skipUnauthorizedEvent: true }))
      return data?.user || (await authService.me())
    }
    await ensureSeed()
    if (!fullName?.trim()) fail('Full name is required.')
    if (!isEmail(email)) fail('Please enter a valid email address.')
    const pw = passwordError(password)
    if (pw) fail(pw)
    const users = getUsers()
    if (users.some((u) => u.email === normalizeEmail(email))) fail('An account with this email already exists.', 409)
    const user = await makeUser(fullName, email, password)
    saveUsers([...users, user])
    write(`products:${user.id}`, [])
    startSession(user)
    return publicUser(user)
  },

  async logout() {
    if (!USE_MOCK) {
      try { await api.post(authPaths.logout, undefined, { skipUnauthorizedEvent: true }) } finally { setAccessToken(null) }
      return
    }
    remove('session')
  },

  /** Local mode returns { demo_reset_token } so the flow is testable without email. */
  async forgotPassword(email) {
    if (!USE_MOCK) return api.post(authPaths.forgotPassword, { email }, { skipUnauthorizedEvent: true })
    await ensureSeed()
    if (!isEmail(email)) fail('Please enter a valid email address.')
    const user = getUsers().find((u) => u.email === normalizeEmail(email))
    if (!user) return { ok: true }
    const token = randomToken()
    const resets = read('resets', []).filter((r) => r.expires_at > Date.now() && r.userId !== user.id)
    write('resets', [...resets, { token, userId: user.id, expires_at: Date.now() + RESET_TTL_MS }])
    return { ok: true, demo_reset_token: token }
  },

  async resetPassword(token, newPassword) {
    if (!USE_MOCK) return api.post(authPaths.resetPassword, { token, new_password: newPassword }, { skipUnauthorizedEvent: true })
    const pw = passwordError(newPassword)
    if (pw) fail(pw)
    const resets = read('resets', [])
    const entry = resets.find((r) => r.token === token && r.expires_at > Date.now())
    if (!entry) fail('This reset link is invalid or has expired. Please request a new one.', 400)
    const users = getUsers()
    const user = users.find((u) => u.id === entry.userId)
    if (!user) fail('This reset link is invalid or has expired. Please request a new one.', 400)
    user.salt = randomToken(16)
    user.hash = await hashPassword(newPassword, user.salt)
    saveUsers(users)
    write('resets', resets.filter((r) => r.token !== token))
    return { ok: true }
  },

  async updateProfile({ name, email }) {
    if (!USE_MOCK) {
      const data = await api.put(authPaths.profile, { full_name: name, email })
      return data?.user || (await authService.me())
    }
    const me = sessionUser()
    if (!name?.trim()) fail('Full name is required.')
    if (!isEmail(email)) fail('Please enter a valid email address.')
    const users = getUsers()
    if (users.some((u) => u.id !== me.id && u.email === normalizeEmail(email))) fail('Another account already uses this email.', 409)
    const user = users.find((u) => u.id === me.id)
    user.name = name.trim()
    user.email = normalizeEmail(email)
    saveUsers(users)
    return publicUser(user)
  },

  async changePassword(current, next) {
    if (!USE_MOCK) return api.post(authPaths.password, { current_password: current, new_password: next })
    const me = sessionUser()
    if ((await hashPassword(current, me.salt)) !== me.hash) fail('Your current password is incorrect.', 400)
    const pw = passwordError(next)
    if (pw) fail(pw)
    const users = getUsers()
    const user = users.find((u) => u.id === me.id)
    user.salt = randomToken(16)
    user.hash = await hashPassword(next, user.salt)
    saveUsers(users)
    return { ok: true }
  },
}
