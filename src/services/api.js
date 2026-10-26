export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const TOKEN_KEY = 'stocklens_access_token'

export const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

/**
 * When no backend URL is configured the app runs entirely in the browser:
 * accounts and data live in localStorage (see services/mockDb.js).
 */
export const USE_MOCK = !baseUrl

let accessToken = null
try { accessToken = localStorage.getItem(TOKEN_KEY) } catch { /* storage unavailable */ }

export const authPaths = {
  me: import.meta.env.VITE_AUTH_ME_PATH || '/api/auth/me',
  login: import.meta.env.VITE_AUTH_LOGIN_PATH || '/api/auth/login',
  register: import.meta.env.VITE_AUTH_REGISTER_PATH || '/api/auth/register',
  forgotPassword: import.meta.env.VITE_AUTH_FORGOT_PATH || '/api/auth/forgot-password',
  resetPassword: import.meta.env.VITE_AUTH_RESET_PATH || '/api/auth/reset-password',
  logout: import.meta.env.VITE_AUTH_LOGOUT_PATH || '/api/auth/logout',
  profile: import.meta.env.VITE_PROFILE_PATH || '/api/auth/profile',
  password: import.meta.env.VITE_PASSWORD_PATH || '/api/auth/change-password',
}

export function setAccessToken(token) {
  accessToken = token || null
  try {
    if (accessToken) localStorage.setItem(TOKEN_KEY, accessToken)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* storage unavailable */ }
}

async function request(path, options = {}) {
  if (USE_MOCK) throw new ApiError('No backend configured (VITE_API_BASE_URL is empty).')
  let response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      credentials: 'include',
      ...options,
      headers: {
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers }),
      },
    })
  } catch {
    throw new ApiError('Unable to connect. Check your connection and try again.')
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (response.status === 401 && !options.skipUnauthorizedEvent) {
    window.dispatchEvent(new CustomEvent('stocklens:unauthorized'))
  }
  if (!response.ok) {
    const detail = Array.isArray(data?.detail) ? data.detail.map((d) => d.msg).join(', ') : data?.detail
    throw new ApiError(detail || data?.message || 'Could not complete this request. Please try again.', response.status)
  }
  return data
}

export const api = {
  get: (path, options) => request(path, options),
  post: (path, body, options) => request(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body), ...options }),
  put: (path, body, options) => request(path, { method: 'PUT', body: JSON.stringify(body), ...options }),
  delete: (path, options) => request(path, { method: 'DELETE', ...options }),
  upload: (path, body, options) => request(path, { method: 'POST', body, ...options }),
}
