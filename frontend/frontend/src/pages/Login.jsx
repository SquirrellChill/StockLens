import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { LockKeyhole } from 'lucide-react'
import AuthLayout from '../components/AuthLayout'
import PasswordField from '../components/PasswordField'
import { useAuth } from '../auth/AuthContext'
import { USE_MOCK } from '../services/api'
import { DEMO_ACCOUNT } from '../services/authService'
import { validateAuthForm } from '../utils/validation'

export default function Login() {
  const { user, checking, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const from = location.state?.from || '/app/dashboard'
  if (!checking && user) return <Navigate to={from} replace />

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    const problem = validateAuthForm('login', form)
    if (problem) return setError(problem)
    setBusy(true)
    try {
      await login(form.email, form.password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Unable to log in. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to continue to your shop.">
      <form onSubmit={submit} noValidate>
        {error && <div className="auth-message error" role="alert">{error}</div>}
        <label>
          <span>Email address</span>
          <input name="email" type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" />
        </label>
        <PasswordField
          name="password"
          label="Password"
          labelExtra={<Link to="/forgot-password">Forgot password?</Link>}
          autoComplete="current-password"
          placeholder="Enter your password"
          value={form.password}
          onChange={(password) => setForm({ ...form, password })}
        />
        <button className="button primary auth-submit" disabled={busy}>{busy ? 'Please wait…' : 'Log in'}</button>
        <p className="auth-switch">New to StockLens? <Link to="/signup">Create account</Link></p>
        {USE_MOCK && (
          <div className="demo-hint">
            Local demo mode — accounts are stored in this browser only.{' '}
            <button type="button" onClick={() => setForm({ email: DEMO_ACCOUNT.email, password: DEMO_ACCOUNT.password })}>Fill demo account</button>
          </div>
        )}
        <div className="auth-note"><LockKeyhole size={14} /> {USE_MOCK ? 'Running without a backend.' : 'Secured by the StockLens backend.'}</div>
      </form>
    </AuthLayout>
  )
}
