import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import AuthLayout from '../components/AuthLayout'
import PasswordField from '../components/PasswordField'
import { useAuth } from '../auth/AuthContext'
import { passwordError } from '../utils/validation'

export default function ResetPassword() {
  const { resetPassword } = useAuth()
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [form, setForm] = useState({ password: '', confirm: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!token) return setError('This reset link is invalid. Please request a new one.')
    const problem = passwordError(form.password)
    if (problem) return setError(problem)
    if (form.password !== form.confirm) return setError('Passwords do not match.')
    setBusy(true)
    try {
      await resetPassword(token, form.password)
      setDone(true)
    } catch (err) {
      setError(err.message || 'Unable to reset your password. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Choose a new password" subtitle="Use at least 8 characters.">
      {done ? (
        <>
          <div className="auth-message success" role="status">Your password has been reset.</div>
          <Link className="button primary auth-submit" to="/login">Log in</Link>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          {error && <div className="auth-message error" role="alert">{error}</div>}
          <PasswordField name="password" label="New password" autoComplete="new-password" placeholder="At least 8 characters" value={form.password} onChange={(password) => setForm({ ...form, password })} />
          <PasswordField name="confirm" label="Confirm new password" autoComplete="new-password" placeholder="Enter it again" value={form.confirm} onChange={(confirm) => setForm({ ...form, confirm })} />
          <button className="button primary auth-submit" disabled={busy}>{busy ? 'Please wait…' : 'Reset password'}</button>
          <p className="auth-switch"><Link to="/login">Back to login</Link></p>
        </form>
      )}
    </AuthLayout>
  )
}
