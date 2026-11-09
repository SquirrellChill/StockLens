import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import AuthLayout from '../components/AuthLayout'
import PasswordField from '../components/PasswordField'
import { useAuth } from '../auth/AuthContext'
<<<<<<< HEAD
=======
import { USE_MOCK } from '../services/api'
>>>>>>> origin/main
import { isEmail, passwordError } from '../utils/validation'

export default function ResetPassword() {
  const { resetPassword, forgotPassword } = useAuth()
  const location = useLocation()
  const [form, setForm] = useState({ email: location.state?.email || '', code: '', password: '', confirm: '' })
  const [demoCode, setDemoCode] = useState(location.state?.demoCode || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [done, setDone] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setInfo('')
    if (!isEmail(form.email)) return setError('Please enter a valid email address.')
    if (!/^\d{6}$/.test(form.code.trim())) return setError('Enter the 6-digit code we sent you.')
    const problem = passwordError(form.password)
    if (problem) return setError(problem)
    if (form.password !== form.confirm) return setError('Passwords do not match.')
    setBusy(true)
    try {
      await resetPassword(form.email, form.code.trim(), form.password)
      setDone(true)
    } catch (err) {
      setError(err.message || 'Unable to reset your password. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const resend = async () => {
    setError('')
    setInfo('')
    if (!isEmail(form.email)) return setError('Enter your email address first.')
    try {
      const res = (await forgotPassword(form.email)) || {}
      setDemoCode(res.demo_reset_code || '')
      setInfo('A new code has been sent if an account exists for this email.')
    } catch (err) {
      setError(err.message || 'Could not send a new code. Please try again.')
    }
  }

  return (
    <AuthLayout title="Reset your password" subtitle="Enter the code from your email and choose a new password.">
      {done ? (
        <>
          <div className="auth-message success" role="status">Your password has been reset. You can now log in.</div>
          <Link className="button primary auth-submit" to="/login">Log in</Link>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          {error && <div className="auth-message error" role="alert">{error}</div>}
          {info && <div className="auth-message success" role="status">{info}</div>}
<<<<<<< HEAD
          {demoCode && <div className="demo-hint">Development mode sends no email. Your code is <b>{demoCode}</b>. It expires in 10 minutes.</div>}
=======
          {USE_MOCK && demoCode && <div className="demo-hint">Demo mode sends no email. Your code is <b>{demoCode}</b>. It expires in 10 minutes.</div>}
>>>>>>> origin/main
          <label><span>Email address</span><input name="email" type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" /></label>
          <label><span>6-digit code</span><input name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.replace(/\D/g, '') })} placeholder="123456" /></label>
          <PasswordField name="password" label="New password" autoComplete="new-password" placeholder="At least 8 characters" value={form.password} onChange={(password) => setForm({ ...form, password })} />
          <PasswordField name="confirm" label="Confirm new password" autoComplete="new-password" placeholder="Enter it again" value={form.confirm} onChange={(confirm) => setForm({ ...form, confirm })} />
          <button className="button primary auth-submit" disabled={busy}>{busy ? 'Please wait…' : 'Reset password'}</button>
          <p className="auth-switch">Didn’t get a code? <button type="button" className="link-button" onClick={resend}>Send again</button></p>
          <p className="auth-switch"><Link to="/login">Back to login</Link></p>
        </form>
      )}
    </AuthLayout>
  )
}
