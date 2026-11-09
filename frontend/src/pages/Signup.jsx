import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'
import AuthLayout from '../components/AuthLayout'
import PasswordField from '../components/PasswordField'
import { useAuth } from '../auth/AuthContext'
import { validateAuthForm } from '../utils/validation'

export default function Signup() {
  const { user, checking, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!checking && user) return <Navigate to="/app/dashboard" replace />

  const set = (key) => (value) => setForm((f) => ({ ...f, [key]: value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    const problem = validateAuthForm('signup', form)
    if (problem) return setError(problem)
    setBusy(true)
    try {
      await register(form.name, form.email, form.password)
      navigate('/app/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || 'Unable to create your account. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Create your account" subtitle="Start managing your stock with confidence.">
      <form onSubmit={submit} noValidate>
        {error && <div className="auth-message error" role="alert">{error}</div>}
        <label><span>Full name</span><input name="name" autoComplete="name" value={form.name} onChange={(e) => set('name')(e.target.value)} placeholder="Your full name" /></label>
        <label><span>Email address</span><input name="email" type="email" autoComplete="email" value={form.email} onChange={(e) => set('email')(e.target.value)} placeholder="you@example.com" /></label>
        <PasswordField name="password" label="Password" autoComplete="new-password" placeholder="At least 8 characters" value={form.password} onChange={set('password')} />
        <PasswordField name="confirm" label="Confirm password" autoComplete="new-password" placeholder="Enter your password again" value={form.confirm} onChange={set('confirm')} />
        <button className="button primary auth-submit" disabled={busy}>{busy ? 'Please wait…' : 'Create account'}</button>
        <p className="auth-switch">Already have an account? <Link to="/login">Log in</Link></p>
      </form>
    </AuthLayout>
  )
}
