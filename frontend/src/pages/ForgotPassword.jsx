import { useState } from 'react'
import { Link } from 'react-router'
import AuthLayout from '../components/AuthLayout'
import { useAuth } from '../auth/AuthContext'
import { USE_MOCK } from '../services/api'
import { validateAuthForm } from '../utils/validation'

export default function ForgotPassword() {
  const { forgotPassword } = useAuth()
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setDone(null)
    const problem = validateAuthForm('forgot', { email })
    if (problem) return setError(problem)
    setBusy(true)
    try {
      setDone((await forgotPassword(email)) || {})
    } catch (err) {
      setError(err.message || 'Unable to complete this request. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Reset your password" subtitle="Enter your email and we’ll send reset instructions.">
      <form onSubmit={submit} noValidate>
        {error && <div className="auth-message error" role="alert">{error}</div>}
        {done && (
          <div className="auth-message success" role="status">
            If an account exists for this email, password reset instructions have been sent.
            {USE_MOCK && done.demo_reset_token && (
              <> <br />Demo mode sends no email — <Link to={`/reset-password?token=${done.demo_reset_token}`}>open your reset link</Link>.</>
            )}
          </div>
        )}
        <label><span>Email address</span><input name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label>
        <button className="button primary auth-submit" disabled={busy}>{busy ? 'Please wait…' : 'Send reset link'}</button>
        <p className="auth-switch"><Link to="/login">Back to login</Link></p>
      </form>
    </AuthLayout>
  )
}
