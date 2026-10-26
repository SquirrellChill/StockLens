const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const MIN_PASSWORD_LENGTH = 8

export function isEmail(value) {
  return EMAIL_RE.test(String(value || '').trim())
}

export function normalizeEmail(value) {
  return String(value || '').trim().toLowerCase()
}

/** Returns an error string, or '' when the password is acceptable. */
export function passwordError(password) {
  if (!password) return 'Password is required.'
  if (password.length < MIN_PASSWORD_LENGTH) return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
  return ''
}

/** Returns an error string for the first problem found, or ''. */
export function validateAuthForm(mode, form) {
  if (mode === 'signup' && !form.name?.trim()) return 'Full name is required.'
  if (!form.email?.trim()) return 'Email address is required.'
  if (!isEmail(form.email)) return 'Please enter a valid email address.'
  if (mode === 'forgot') return ''
  if (mode === 'login') return form.password ? '' : 'Password is required.'
  const pw = passwordError(form.password)
  if (pw) return pw
  if (form.password !== form.confirm) return 'Passwords do not match.'
  return ''
}

export function validateProduct(form) {
  if (!String(form.name || '').trim() || form.quantity === '' || form.unit_price === '') {
    return 'Please complete all required fields.'
  }
  if (Number(form.quantity) < 0 || Number(form.unit_price) < 0 || Number.isNaN(Number(form.quantity)) || Number.isNaN(Number(form.unit_price))) {
    return 'Please enter a valid non-negative number.'
  }
  return ''
}
