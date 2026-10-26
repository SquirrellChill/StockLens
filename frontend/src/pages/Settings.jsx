import { useState } from 'react'
import { useNavigate } from 'react-router'
import { AlertTriangle, CheckCircle2, LogOut } from 'lucide-react'
import Button from '../components/Button'
import Modal from '../components/Modal'
import PasswordField from '../components/PasswordField'
import { useAuth } from '../auth/AuthContext'
import { isEmail, passwordError } from '../utils/validation'

export default function Settings() {
  const { user, updateProfile, changePassword, logout } = useAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState({ name: user?.name || user?.full_name || '', email: user?.email || '' })
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState(null)
  const [confirmLogout, setConfirmLogout] = useState(false)

  const say = (type, text) => setMessage({ type, text })

  const saveProfile = async (e) => {
    e.preventDefault()
    setMessage(null)
    if (!profile.name.trim() || !profile.email.trim()) return say('error', 'Name and email are required.')
    if (!isEmail(profile.email)) return say('error', 'Please enter a valid email address.')
    setBusy('profile')
    try { await updateProfile(profile); say('success', 'Your profile has been updated.') }
    catch (err) { say('error', err.message) }
    finally { setBusy('') }
  }

  const savePassword = async (e) => {
    e.preventDefault()
    setMessage(null)
    if (!pw.current || !pw.next) return say('error', 'Complete all password fields.')
    const problem = passwordError(pw.next)
    if (problem) return say('error', problem.replace('Password', 'New password'))
    if (pw.next !== pw.confirm) return say('error', 'New passwords do not match.')
    setBusy('password')
    try { await changePassword(pw.current, pw.next); setPw({ current: '', next: '', confirm: '' }); say('success', 'Your password has been changed.') }
    catch (err) { say('error', err.message) }
    finally { setBusy('') }
  }

  const doLogout = async () => {
    setBusy('logout')
    await logout()
    navigate('/', { replace: true })
  }

  const initials = (profile.name || profile.email || 'U').slice(0, 2).toUpperCase()

  return (
    <>
      <div className="title-row"><div><h1>Settings</h1><p>Manage your account and security.</p></div></div>
      {message && <div className={`settings-message ${message.type}`} role={message.type === 'error' ? 'alert' : 'status'}>{message.type === 'success' ? <CheckCircle2 /> : <AlertTriangle />}<span>{message.text}</span></div>}
      <div className="settings-grid">
        <section className="panel settings-profile">
          <div className="settings-section-head"><h2>Profile information</h2><p>Update how your account appears in StockLens.</p></div>
          <div className="profile-summary"><span>{initials}</span><div><strong>{user?.name || user?.full_name || 'StockLens user'}</strong><small>{user?.email}</small></div></div>
          <form className="settings-form" onSubmit={saveProfile} noValidate>
            <label><span>Full name</span><input name="name" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} /></label>
            <label><span>Email address</span><input name="email" type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} /></label>
            <Button type="submit" disabled={busy === 'profile'}>{busy === 'profile' ? 'Saving…' : 'Save changes'}</Button>
          </form>
        </section>
        <section className="panel settings-profile">
          <div className="settings-section-head"><h2>Change password</h2><p>Use a strong password you do not reuse elsewhere.</p></div>
          <form className="settings-form" onSubmit={savePassword} noValidate>
            <PasswordField name="current" label="Current password" autoComplete="current-password" value={pw.current} onChange={(current) => setPw({ ...pw, current })} />
            <PasswordField name="next" label="New password" autoComplete="new-password" value={pw.next} onChange={(next) => setPw({ ...pw, next })} />
            <PasswordField name="confirm" label="Confirm new password" autoComplete="new-password" value={pw.confirm} onChange={(confirm) => setPw({ ...pw, confirm })} />
            <Button type="submit" disabled={busy === 'password'}>{busy === 'password' ? 'Updating…' : 'Change password'}</Button>
          </form>
        </section>
      </div>
      <section className="panel logout-panel">
        <div><strong>Log out of StockLens</strong><p>You will need to log in again to access your shop.</p></div>
        <Button kind="danger" icon={LogOut} onClick={() => setConfirmLogout(true)}>Log out</Button>
      </section>
      {confirmLogout && (
        <Modal onClose={() => setConfirmLogout(false)} className="confirm-modal" label="Log out">
          <span className="confirm-icon"><LogOut /></span>
          <h2>Log out of StockLens?</h2>
          <p>You’ll be returned to the public landing page.</p>
          <div className="modal-actions">
            <Button kind="secondary" onClick={() => setConfirmLogout(false)}>Cancel</Button>
            <Button kind="danger" disabled={busy === 'logout'} onClick={doLogout}>{busy === 'logout' ? 'Logging out…' : 'Log out'}</Button>
          </div>
        </Modal>
      )}
    </>
  )
}
