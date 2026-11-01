import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import AuthLayout from '../components/AuthLayout'
import { useAuth } from '../auth/AuthContext'
import { validateAuthForm } from '../utils/validation'

export default function ForgotPassword() {
  const { forgotPassword } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    const problem = validateAuthForm('forgot', { email })
    if (problem) return setError(problem)
    setBusy(true)
    try {
      const res = (await forgotPassword(email)) || {}
      // Same response whether or not the account exists; continue to the code step.
      navigate('/reset-password', { state: { email: email.trim(), demoCode: res.demo_reset_code || '' } })
    } catch (err) {
      setError(err.message || 'Unable to complete this request. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Forgot your password?" subtitle="Enter your email and we’ll send you a 6-digit code.">
      <form onSubmit={submit} noValidate>
        {error && <div className="auth-message error" role="alert">{error}</div>}
        <label><span>Email address</span><input name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label>
        <button className="button primary auth-submit" disabled={busy}>{busy ? 'Please wait…' : 'Send code'}</button>
        <p className="auth-switch"><Link to="/login">Back to login</Link></p>
      </form>
    </AuthLayout>
  )
}
